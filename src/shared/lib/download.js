// File downloads from the browser: a click on a hidden link with the download attribute.

// Downloads an object URL (from URL.createObjectURL) and releases it afterwards
export function downloadObjectUrl(url, fileName) {
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();
    link.remove();
    // only once the browser has started the download
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Downloads data (a string, ArrayBuffer, typed array or Blob) as a file
export function downloadData(
    data,
    fileName,
    type = "application/octet-stream",
) {
    downloadObjectUrl(
        URL.createObjectURL(new Blob([data], { type })),
        fileName,
    );
}
