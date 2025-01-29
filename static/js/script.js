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

    // Logout functionality (simple redirect to login)
    const logoutLink = document.getElementById('logout-link');
    if (logoutLink) {
        logoutLink.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = '/logout'; // Implement logout route if needed
        });
    }
});