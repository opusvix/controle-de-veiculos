-- ============================================================================
-- Controle de Veículos — banco na nuvem (Supabase / PostgreSQL)
-- Rascunho da modelagem para dados COMPARTILHADOS entre aparelhos/motoristas.
--
-- Princípios:
--  • Multi-tenant por CONTA (empresa): cada linha carrega conta_id; a RLS
--    garante que um usuário só enxerga a sua conta. Vários motoristas podem
--    fazer login na mesma conta.
--  • Ids em TEXT: o app continua gerando ids no cliente (uid()), o que mantém
--    o modo offline-first — cria offline e sincroniza depois, sem conflito de
--    chave auto-incremento.
--  • Mesmos campos do modelo atual (localStorage / app Windows), para o
--    round-trip continuar valendo.
-- ============================================================================

-- Conta = a "empresa"/espaço de dados. Um usuário pertence a uma conta.
create table if not exists contas (
  id          text primary key,
  nome        text not null default 'Minha frota',
  criada_em   timestamptz not null default now()
);

-- Perfil do usuário autenticado (id = auth.users.id do Supabase Auth).
create table if not exists usuarios (
  id          uuid primary key references auth.users (id) on delete cascade,
  conta_id    text not null references contas (id) on delete cascade,
  nome        text,
  papel       text not null default 'membro',   -- 'dono' | 'membro'
  criado_em   timestamptz not null default now()
);

create table if not exists veiculos (
  id              text primary key,
  conta_id        text not null references contas (id) on delete cascade,
  name            text not null default '',
  plate           text default '',
  year            int,
  fuel            text default 'Gasolina',
  initial_km      numeric default 0,
  tank_capacity   numeric default 0,
  notes           text default '',
  atualizado_em   timestamptz not null default now()
);

create table if not exists motoristas (
  id              text primary key,
  conta_id        text not null references contas (id) on delete cascade,
  name            text not null default '',
  license         text default '',
  notes           text default '',
  atualizado_em   timestamptz not null default now()
);

create table if not exists abastecimentos (
  id              text primary key,
  conta_id        text not null references contas (id) on delete cascade,
  vehicle_id      text references veiculos (id) on delete cascade,
  driver_id       text,                         -- motorista (quem abasteceu)
  date            date,
  odometer        numeric default 0,
  liters          numeric default 0,
  price           numeric default 0,
  total           numeric default 0,
  full_tank       boolean default false,
  station         text default '',
  notes           text default '',
  atualizado_em   timestamptz not null default now()
);

create table if not exists manutencoes (
  id              text primary key,
  conta_id        text not null references contas (id) on delete cascade,
  vehicle_id      text references veiculos (id) on delete cascade,
  date            date,
  odometer        numeric default 0,
  type            text default '',
  details         text default '',
  cost            numeric default 0,
  shop            text default '',
  notes           text default '',
  next_km         numeric,
  next_date       date,
  atualizado_em   timestamptz not null default now()
);

create table if not exists documentos (
  id              text primary key,
  conta_id        text not null references contas (id) on delete cascade,
  vehicle_id      text references veiculos (id) on delete cascade,
  type            text default '',
  due_date        date,
  cost            numeric default 0,
  notes           text default '',
  done            boolean default false,
  atualizado_em   timestamptz not null default now()
);

create index if not exists idx_veiculos_conta       on veiculos (conta_id);
create index if not exists idx_motoristas_conta     on motoristas (conta_id);
create index if not exists idx_abastecimentos_conta on abastecimentos (conta_id);
create index if not exists idx_manutencoes_conta    on manutencoes (conta_id);
create index if not exists idx_documentos_conta     on documentos (conta_id);

-- ============================================================================
-- Row-Level Security: cada usuário só vê/edita a SUA conta.
-- ============================================================================
create or replace function conta_do_usuario()
returns text
language sql stable
as $$ select conta_id from usuarios where id = auth.uid() $$;

alter table contas         enable row level security;
alter table usuarios       enable row level security;
alter table veiculos       enable row level security;
alter table motoristas     enable row level security;
alter table abastecimentos enable row level security;
alter table manutencoes    enable row level security;
alter table documentos     enable row level security;

-- O usuário enxerga a própria linha de perfil.
create policy usuarios_self on usuarios
  for select using (id = auth.uid());

-- A conta visível é a do usuário.
create policy contas_propria on contas
  for select using (id = conta_do_usuario());

-- Tabelas de dados: tudo filtrado por conta_id = conta do usuário.
do $$
declare t text;
begin
  foreach t in array array['veiculos','motoristas','abastecimentos','manutencoes','documentos']
  loop
    execute format($f$
      create policy %1$s_rw on %1$s
        using (conta_id = conta_do_usuario())
        with check (conta_id = conta_do_usuario());
    $f$, t);
  end loop;
end $$;

-- ============================================================================
-- Provisionamento automático: ao criar um usuário (signup), cria a CONTA
-- (empresa) e o perfil 'dono'. Assim o cadastro já nasce com um espaço de
-- dados próprio, sem o cliente precisar inserir em contas/usuarios (o que a
-- RLS bloquearia). security definer roda com privilégio para contornar a RLS
-- só aqui dentro.
-- ============================================================================
create extension if not exists pgcrypto;

create or replace function handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
declare nova_conta text;
begin
  nova_conta := replace(gen_random_uuid()::text, '-', '');
  insert into contas (id, nome)
    values (nova_conta,
            coalesce(nullif(new.raw_user_meta_data->>'empresa', ''), 'Minha frota'));
  insert into usuarios (id, conta_id, nome, papel)
    values (new.id, nova_conta, new.raw_user_meta_data->>'nome', 'dono');
  return new;
end $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function handle_new_user();

-- Nota: neste primeiro momento, cada cadastro cria uma conta nova. Para vários
-- motoristas na MESMA empresa, ou (a) compartilham um login da empresa, ou
-- (b) implementamos convites (próximo passo): um usuário novo entra numa conta
-- existente em vez de criar uma.
