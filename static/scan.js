document.addEventListener("DOMContentLoaded", function() {
    const video = document.getElementById('qr-video');
    const feedbackMessage = document.getElementById('feedback-message');
    const scanButton = document.getElementById('scan-button');
    const stopButton = document.getElementById('stop-button');

    let scanning = false;
    let scannedCodes = new Set();

    // Start scanning when the scan button is clicked
    scanButton.addEventListener('click', function() {
        scanning = true;
        feedbackMessage.innerText = 'Scanning QR code...';
        scanQRCode();
    });

    // Stop scanning when the stop button is clicked
    stopButton.addEventListener('click', function() {
        scanning = false;
        feedbackMessage.innerText = 'Scanning stopped.';
    });

    // Function to scan QR code
    function scanQRCode() {
        const constraints = {
            video: { facingMode: "environment" }
        };

        navigator.mediaDevices.getUserMedia(constraints)
            .then(function(stream) {
                video.srcObject = stream;
                video.play();

                const canvasElement = document.createElement('canvas');
                const canvas = canvasElement.getContext('2d');

                const checkQRCode = () => {
                    if (!scanning) {
                        return;
                    }

                    canvasElement.width = video.videoWidth;
                    canvasElement.height = video.videoHeight;
                    canvas.drawImage(video, 0, 0, canvasElement.width, canvasElement.height);
                    const imageData = canvas.getImageData(0, 0, canvasElement.width, canvasElement.height);
                    const code = jsQR(imageData.data, imageData.width, imageData.height, {
                        inversionAttempts: "dontInvert",
                    });

                    if (code) {
                        const qrData = code.data;
                        if (scannedCodes.has(qrData)) {
                            feedbackMessage.innerText = 'QR code already scanned.';
                        } else {
                            feedbackMessage.innerText = 'QR code scanned successfully: ' + qrData;
                            scannedCodes.add(qrData);
                            // Call backend API to check attendance and perform further actions
                        }
                    }

                    requestAnimationFrame(checkQRCode);
                };

                checkQRCode();
            })
            .catch(function(err) {
                console.error('Error accessing camera:', err);
            });
    }
});
