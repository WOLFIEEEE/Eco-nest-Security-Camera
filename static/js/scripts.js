document.addEventListener('DOMContentLoaded', () => {
    let currentPage = 1;
    const perPage = 20;

    const anomaliesGrid = document.getElementById('anomalies-grid');
    const showMoreButton = document.getElementById('show-more');

    // Function to fetch and display anomalies
    function loadAnomalies(page) {
        fetch(`/get_anomalies?page=${page}&per_page=${perPage}`)
            .then(response => response.json())
            .then(data => {
                data.images.forEach(image => {
                    const img = document.createElement('img');
                    img.src = image.url;
                    img.alt = 'Anomaly';
                    img.className = 'anomaly-image';
                    img.dataset.filename = image.filename;
                    img.dataset.timestamp = image.timestamp;
                    anomaliesGrid.appendChild(img);
                });
                // If no more images, hide the Show More button
                if (data.images.length < perPage) {
                    showMoreButton.style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Error fetching anomalies:', error);
            });
    }

    // Initial load
    loadAnomalies(currentPage);

    // Show More button click
    showMoreButton.addEventListener('click', () => {
        currentPage += 1;
        loadAnomalies(currentPage);
    });

    // Handle anomaly image click
    anomaliesGrid.addEventListener('click', (e) => {
        if (e.target && e.target.classList.contains('anomaly-image')) {
            const filename = e.target.dataset.filename;
            window.location.href = `/anomaly/${filename}`;
        }
    });

    // Logout functionality (simple redirect to login)
    const logoutLink = document.getElementById('logout-link');
    if (logoutLink) {
        logoutLink.addEventListener('click', (e) => {
            e.preventDefault();
            // Since HTTP Basic Auth doesn't support logout, prompt the user to close the browser or use incognito
            alert('To logout, please close the browser or use a private/incognito window.');
        });
    }
});