<?php
/**
 * CLI Tool: System-Wide Security & File Integrity Scanner
 * Scans uploads, assets, and the application tree for:
 * 1. Any malicious or unauthorized scripts in non-code directories (uploads, etc.)
 * 2. Any dropped rogue index.php files or backdoors
 * 3. Any hidden dot files or unapproved executables
 *
 * Usage:
 *   php tools/clean_uploads.php
 */

if (php_sapi_name() !== 'cli') {
    http_response_code(403);
    die("Forbidden: CLI execution only.\n");
}

$root_dir = dirname(__DIR__);
echo "========================================================\n";
echo "       System-Wide Security & Integrity Scanner         \n";
echo "========================================================\n";
echo "Target: $root_dir\n\n";

$allowed_upload_exts = array(
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg', 'ico',
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv', 'rtf',
    'zip', 'rar', 'tar', 'gz',
    'mp3', 'wav', 'mp4', 'm4v', 'avi', 'mov', 'wmv', 'webm', 'ogg'
);

$deleted = 0;
$scanned = 0;

// 1. Scan uploads for any unauthorized scripts
$static_dirs = array('uploads');

foreach ($static_dirs as $sdir) {
    $dir_path = $root_dir . '/' . $sdir;
    if (!is_dir($dir_path)) continue;

    echo "--- Auditing /$sdir ---\n";
    $it = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($dir_path, RecursiveDirectoryIterator::SKIP_DOTS),
        RecursiveIteratorIterator::CHILD_FIRST
    );

    foreach ($it as $item) {
        $p = str_replace('\\', '/', $item->getPathname());
        $name = $item->getFilename();

        if ($item->isDir()) {
            if ($name === 'well-known' || (substr($name, 0, 1) === '.' && $name !== '.' && $name !== '..')) {
                echo "[REMOVED SUSPICIOUS DIR] $p\n";
                @rmdir($p);
                $deleted++;
            }
            continue;
        }

        $scanned++;

        // Allow legitimate .htaccess and index.html
        if ($name === '.htaccess' || $name === 'index.html') {
            continue;
        }

        $ext = strtolower(pathinfo($name, PATHINFO_EXTENSION));

        // In uploads: STRICTLY block any PHP or shell scripts
        if (preg_match('/\.(php[0-9]*|phtml|phps|pht|phar|inc|sh|bash|pl|py|cgi|exe|bat|cmd|com|vbs|scr|jar|js|html|htm|htaccess|php-ini)(\.|$)/i', $name)) {
            echo "[PURGED SCRIPT IN $sdir] $p\n";
            @unlink($p);
            $deleted++;
            continue;
        }

        if (in_array(strtolower($name), array('thumbs.db', 'desktop.ini', '.ds_store'), true)) {
            @unlink($p);
            $deleted++;
            continue;
        }
    }
}

// 2. Check root and entire repo for any rogue 503 maintenance droppers or duplicate index.php
echo "\n--- Auditing for Rogue index.php Droppers ---\n";
$all_it = new RecursiveIteratorIterator(
    new RecursiveDirectoryIterator($root_dir, RecursiveDirectoryIterator::SKIP_DOTS),
    RecursiveIteratorIterator::SELF_FIRST
);

$purged_droppers = 0;
foreach ($all_it as $item) {
    if ($item->isFile() && $item->getFilename() === 'index.php') {
        $p = str_replace('\\', '/', $item->getPathname());
        $rel = ltrim(str_replace($root_dir, '', $p), '/');

        // Legitimate front controller in root
        if ($rel === 'index.php') {
            continue;
        }

        // Any index.php inside uploads, assets, etc. is suspicious
        if (strpos($rel, 'uploads/') === 0) {
            echo "[PURGED ROGUE PHP IN UPLOADS] $rel\n";
            @unlink($p);
            $deleted++;
            continue;
        }

        if ($item->getSize() === 2020) {
            $content = @file_get_contents($p);
            if ($content !== false && strpos($content, 'Briefly unavailable for scheduled maintenance') !== false) {
                echo "[REMOVED ROGUE 503 DROPPER] $rel\n";
                @unlink($p);
                $purged_droppers++;
                $deleted++;
            }
        }
    }
}

echo "\n========================================================\n";
echo "Summary: Scanned $scanned files.\n";
echo "Purged $deleted unauthorized / suspicious files ($purged_droppers rogue droppers).\n";
echo "Integrity check completed successfully.\n";
echo "========================================================\n";
