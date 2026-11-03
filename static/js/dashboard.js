/**
 * Dashboard Analytics and Visualization Scripts (Chart.js)
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Topic Mastery Bar Chart
    const masteryCanvas = document.getElementById('topicMasteryChart');
    if (masteryCanvas && window.dashboardChartData) {
        const ctx = masteryCanvas.getContext('2d');
        const data = window.dashboardChartData;
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Mastery Level (%)',
                    data: data.mastery,
                    backgroundColor: data.colors,
                    borderRadius: 8,
                    borderSkipped: false,
                    maxBarThickness: 32
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        padding: 10,
                        cornerRadius: 8,
                        titleFont: { family: 'Outfit, sans-serif', weight: 'bold' },
                        bodyFont: { family: 'Outfit, sans-serif' },
                        callbacks: {
                            label: function(context) {
                                return ` Topic Mastery: ${context.raw}%`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: value => `${value}%`,
                            font: { family: 'Outfit, sans-serif' }
                        },
                        grid: { color: '#f1f5f9' }
                    },
                    x: {
                        ticks: {
                            font: { family: 'Outfit, sans-serif', size: 11 },
                            maxRotation: 30,
                            minRotation: 0
                        },
                        grid: { display: false }
                    }
                }
            }
        });
    }

    // 2. Score History Progress Line Chart
    const trendCanvas = document.getElementById('scoreTrendChart');
    if (trendCanvas && window.dashboardTrendData && window.dashboardTrendData.dates.length > 0) {
        const ctx = trendCanvas.getContext('2d');
        const trend = window.dashboardTrendData;

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: trend.dates,
                datasets: [{
                    label: 'Score Percentage',
                    data: trend.scores,
                    fill: true,
                    backgroundColor: 'rgba(67, 97, 238, 0.12)',
                    borderColor: '#4361ee',
                    borderWidth: 3,
                    pointBackgroundColor: '#4361ee',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    tension: 0.35
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        padding: 10,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(context) {
                                return ` Score: ${context.raw}%`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: value => `${value}%`,
                            font: { family: 'Outfit, sans-serif' }
                        },
                        grid: { color: '#f1f5f9' }
                    },
                    x: {
                        ticks: {
                            font: { family: 'Outfit, sans-serif' }
                        },
                        grid: { display: false }
                    }
                }
            }
        });
    }
});
