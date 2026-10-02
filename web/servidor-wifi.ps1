# Servidor Wi-Fi do Controle de Veículos (sem Python).
# Usa apenas o PowerShell que ja vem com o Windows 10/11.
# Sobe na porta 8000, mostra o endereco para o celular e serve esta pasta.
#
# Executado pelo "Servidor Wi-Fi.bat" quando o Python nao esta instalado.

$pasta = Split-Path -Parent $MyInvocation.MyCommand.Path
$porta = 8000

function Obter-IP {
    try {
        $udp = New-Object Net.Sockets.UdpClient
        try {
            $udp.Connect("8.8.8.8", 80)
            $ip = $udp.Client.LocalEndPoint.Address.ToString()
        } finally {
            $udp.Close()
        }
        if ($ip -and -not $ip.StartsWith("127.")) { return $ip }
    } catch { }
    try {
        $rede = [System.Net.Dns]::GetHostEntry([System.Net.Dns]::GetHostName()).AddressList |
            Where-Object { $_.AddressFamily -eq "InterNetwork" } |
            Select-Object -First 1
        if ($rede) { return $rede.IPAddressToString }
    } catch { }
    return "127.0.0.1"
}

function Tipos-De-Arquivo {
    return @{
        ".html" = "text/html; charset=utf-8"
        ".htm"  = "text/html; charset=utf-8"
        ".csv"  = "text/csv; charset=utf-8"
        ".tsv"  = "text/csv; charset=utf-8"
        ".json" = "application/json; charset=utf-8"
        ".txt"  = "text/plain; charset=utf-8"
        ".md"   = "text/plain; charset=utf-8"
        ".js"   = "text/javascript; charset=utf-8"
        ".css"  = "text/css; charset=utf-8"
        ".svg"  = "image/svg+xml"
        ".png"  = "image/png"
        ".jpg"  = "image/jpeg"
        ".ico"  = "image/x-icon"
        ".xlsx" = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ".pdf"  = "application/pdf"
    }
}

$ip = Obter-IP
$url = "http://${ip}:${porta}/controle-veiculos.html"
$mime = Tipos-De-Arquivo

Write-Host ""
Write-Host "   No celular, abra o navegador e digite:"
Write-Host ""
Write-Host "        $url" -ForegroundColor Cyan
Write-Host ""
Write-Host "   * celular e PC precisam estar na mesma rede Wi-Fi"
Write-Host "   * para encerrar, feche esta janela ou pressione Ctrl+C"
Write-Host ""
Write-Host "  --------------------------------------------------"
Write-Host ""

$servidor = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any, $porta)
try {
    $servidor.Start()
} catch {
    Write-Host "  Nao foi possivel abrir a porta $porta : $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Talvez outro programa ja esteja usando. Feche e tente de novo."
    Read-Host "Pressione Enter para fechar"
    exit 1
}

Write-Host "  Servidor ligado. Atendendo pedidos..."

try {
    while ($true) {
        $cliente = $null
        try {
            $cliente = $servidor.AcceptTcpClient()
            $cliente.ReceiveTimeout = 8000
            $fluxo = $cliente.GetStream()
            $buffer = New-Object byte[] 8192
            $total = 0
            while ($total -lt 8192) {
                $n = $fluxo.Read($buffer, $total, 8192 - $total)
                if ($n -le 0) { break }
                $total += $n
                $pedido = [System.Text.Encoding]::ASCII.GetString($buffer, 0, $total)
                if ($pedido -match "`r?`n`r?`n") { break }
            }
            if ($total -eq 0) { continue }

            $primeira = ([System.Text.Encoding]::ASCII.GetString($buffer, 0, $total) -split "`r?`n")[0]
            $partes = $primeira.Trim() -split "\s+"
            if ($partes.Count -lt 2) { continue }
            $metodo = $partes[0].ToUpper()
            $caminho = ($partes[1] -split "\?")[0]
            $caminho = [System.Uri]::UnescapeDataString($caminho)

            $relativo = $caminho.Replace("/", "\").TrimStart("\")
            if ($relativo -eq "") { $relativo = "controle-veiculos.html" }
            $completo = [System.IO.Path]::GetFullPath((Join-Path $pasta $relativo))
            $raiz = [System.IO.Path]::GetFullPath($pasta)

            $corpo = $null
            $status = "200 OK"
            $tipo = "text/plain; charset=utf-8"
            if (-not $completo.StartsWith($raiz, [System.StringComparison]::OrdinalIgnoreCase)) {
                $status = "403 Forbidden"
                $corpo = [System.Text.Encoding]::UTF8.GetBytes("403")
            } elseif ($metodo -ne "GET" -and $metodo -ne "HEAD") {
                $status = "405 Method Not Allowed"
                $corpo = [System.Text.Encoding]::UTF8.GetBytes("405")
            } elseif (-not (Test-Path -LiteralPath $completo -PathType Leaf)) {
                $status = "404 Not Found"
                $corpo = [System.Text.Encoding]::UTF8.GetBytes("404 - arquivo nao encontrado")
            } else {
                $corpo = [System.IO.File]::ReadAllBytes($completo)
                $extensao = [System.IO.Path]::GetExtension($completo).ToLower()
                if ($mime.ContainsKey($extensao)) { $tipo = $mime[$extensao] }
            }

            $cabecalho = "HTTP/1.1 $status`r`n" +
                "Server: controle-veiculos`r`n" +
                "Content-Type: $tipo`r`n" +
                "Content-Length: $($corpo.Length)`r`n" +
                "Connection: close`r`n`r`n"
            $bytesCabecalho = [System.Text.Encoding]::ASCII.GetBytes($cabecalho)
            $fluxo.Write($bytesCabecalho, 0, $bytesCabecalho.Length)
            if ($metodo -ne "HEAD" -and $corpo.Length -gt 0) {
                $fluxo.Write($corpo, 0, $corpo.Length)
            }
            $fluxo.Flush()
        } catch {
            # pedido incompleto/erro de rede: ignora e segue atendendo
        } finally {
            if ($cliente) {
                try { $cliente.Close() } catch { }
            }
        }
    }
} finally {
    try { $servidor.Stop() } catch { }
    Write-Host ""
    Write-Host "  Servidor encerrado."
}
