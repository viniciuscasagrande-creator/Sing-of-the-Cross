$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$mobile = Join-Path $root "mobile"
$build = Join-Path $mobile "build"

$javaBin = "C:\Program Files\Android\Android Studio\jbr\bin"
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:PATH = "$javaBin;$env:PATH"

$sdk = "C:\Users\vinad\AppData\Local\Android\Sdk"
$bt = Join-Path $sdk "build-tools\36.0.0"
$androidJar = Join-Path $sdk "platforms\android-36.1\android.jar"

$aapt2 = Join-Path $bt "aapt2.exe"
$d8 = Join-Path $bt "d8.bat"
$zipalign = Join-Path $bt "zipalign.exe"
$apksigner = Join-Path $bt "apksigner.bat"
$javac = Join-Path $javaBin "javac.exe"
$jar = Join-Path $javaBin "jar.exe"
$keytool = Join-Path $javaBin "keytool.exe"

if (Test-Path $build) { Remove-Item $build -Recurse -Force }
New-Item -ItemType Directory -Force -Path "$build\gen", "$build\obj", "$build\dex", "$mobile\res\drawable" | Out-Null

# 1. Gerar icone PNG 192x192 a partir do logo.png oficial
Add-Type -AssemblyName System.Drawing
$srcLogo = Join-Path $root "frontend\assets\logo.png"
$dstIcon = Join-Path $mobile "res\drawable\ic_launcher.png"
$img = [System.Drawing.Image]::FromFile($srcLogo)
$bmp = New-Object System.Drawing.Bitmap(192, 192)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.Clear([System.Drawing.Color]::FromArgb(255, 8, 8, 8))
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.DrawImage($img, 0, 0, 192, 192)
$g.Dispose()
$bmp.Save($dstIcon, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
$img.Dispose()
Write-Host "[1/6] Icone Dark Gothic 192x192 gerado com sucesso."

# 2. Compilar e linkar recursos com AAPT2
$compiledZip = Join-Path $build "compiled_res.zip"
$unalignedApk = Join-Path $build "unaligned.apk"
& $aapt2 compile --dir "$mobile\res" -o $compiledZip
& $aapt2 link -o $unalignedApk -I $androidJar --manifest "$mobile\AndroidManifest.xml" --java "$build\gen" $compiledZip --auto-add-overlay
Write-Host "[2/6] Recursos e AndroidManifest.xml vinculados via AAPT2."

# 3. Compilar classes Java (R.java + MainActivity.java) com JDK 21 (target Java 8 bytecode para D8)
$javaFiles = @(
    (Join-Path $build "gen\com\sotc\commandcenter\R.java"),
    (Join-Path $mobile "src\com\sotc\commandcenter\MainActivity.java")
)
& $javac -source 1.8 -target 1.8 -encoding UTF-8 -cp $androidJar -d "$build\obj" $javaFiles
Write-Host "[3/6] Codigo Java compilado com OpenJDK 21."

# 4. Converter .class para classes.dex usando D8
$classFiles = Get-ChildItem -Path "$build\obj" -Recurse -Filter "*.class" | ForEach-Object { $_.FullName }
& $d8 --lib $androidJar --output "$build\dex" $classFiles
Write-Host "[4/6] Bytecode DEX (classes.dex) gerado via D8."

# 5. Inserir classes.dex dentro do APK e alinhar com zipalign (4-byte alignment)
& $jar -uf $unalignedApk -C "$build\dex" classes.dex

$alignedApk = Join-Path $build "aligned.apk"
& $zipalign -f -p 4 $unalignedApk $alignedApk
Write-Host "[5/6] APK empacotado e alinhado com zipalign."

# 6. Gerar Keystore de producao SOTC e assinar APK (v1 + v2 + v3) com apksigner
$keystore = Join-Path $mobile "sotc-release.keystore"
if (-not (Test-Path $keystore)) {
    & $keytool -genkeypair -v -keystore $keystore -alias sotckey -keyalg RSA -keysize 2048 -validity 10000 -storepass sotc123456 -keypass sotc123456 -dname "CN=Sing Of The Cross, OU=Multi-Cloud Command Center, O=SOTC, L=Curitiba, ST=PR, C=BR"
}

$finalApkRoot = Join-Path $root "SingOfTheCross.apk"
$finalApkAssets = Join-Path $root "frontend\assets\SingOfTheCross.apk"
$finalApkDesktop = "C:\Users\vinad\Desktop\SingOfTheCross.apk"

& $apksigner sign --ks $keystore --ks-key-alias sotckey --ks-pass pass:sotc123456 --key-pass pass:sotc123456 --out $finalApkRoot $alignedApk
& $apksigner verify --verbose $finalApkRoot

Copy-Item -Path $finalApkRoot -Destination $finalApkAssets -Force
Copy-Item -Path $finalApkRoot -Destination $finalApkDesktop -Force
Remove-Item $build -Recurse -Force

Write-Host "[6/6] APK ASSINADO E VERIFICADO COM SUCESSO!"
Get-Item $finalApkRoot, $finalApkDesktop | Select-Object FullName, Length, LastWriteTime
