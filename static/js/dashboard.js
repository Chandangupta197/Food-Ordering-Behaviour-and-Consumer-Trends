const dataNode = document.getElementById("chart-data");
if (dataNode) {
  const charts = JSON.parse(dataNode.textContent);
  const makeChart = (id, dataset, label) => {
    const canvas = document.getElementById(id);
    if (!canvas || !dataset.labels.length) return;
    new Chart(canvas, {
      type: "bar",
      data: { labels: dataset.labels, datasets: [{ label, data: dataset.values, borderWidth: 1, borderRadius: 6 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
    });
  };
  makeChart("cuisineChart", charts.cuisine, "Orders");
  makeChart("cityChart", charts.city, "Orders");
  makeChart("mealChart", charts.meal, "Orders");
}
