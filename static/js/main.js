(function ($) {
  "use strict";

  // meanmenu
  $("#mobile-menu").meanmenu({
    meanMenuContainer: ".mobile-menu",
    meanScreenWidth: "1400",
  });

  //mobile side menu
  $(".side-toggle").on("click", function () {
    $(".side-info").addClass("info-open");
    $(".offcanvas-overlay").addClass("overlay-open");
  });

  $(".side-info-close,.offcanvas-overlay").on("click", function () {
    $(".side-info").removeClass("info-open");
    $(".offcanvas-overlay").removeClass("overlay-open");
  });


  function reveal() {
    var reveals = document.querySelectorAll(".reveal");
    for (var i = 0; i < reveals.length; i++) {
      var windowHeight = window.innerHeight;
      var elementTop = reveals[i].getBoundingClientRect().top;
      var elementVisible = 150;
      if (elementTop < windowHeight - elementVisible) {
        reveals[i].classList.add("active");
      } 
      // else {
      //   reveals[i].classList.remove("active");
      // }
    }
  }

  window.addEventListener("scroll", reveal);

// To check the scroll position on page load
reveal();


})(jQuery);

// =============================================================

var ctxDoughnut = document.getElementById('doughnutChart').getContext('2d');
var doughnutChart = new Chart(ctxDoughnut, {
    type: 'doughnut',
    data: {
        labels: ['6.9%', '93.1%', '10%', '5%', '50%'],
        datasets: [{
            // label: 'Votes',
            data: [6.9, 93.1, ],
            backgroundColor: [
                '#02DE11',
                '#64DAFF'
            ],
            borderWidth: 0,
            hoverOffset: 4
        }]
    },
    options: {
      responsive: true,
      cutout: '90%',
      layout: {
        padding: {
            top: 0,   
            bottom: 40, 
            left: 90, 
            right: 90
        }
    },
      plugins: {
          legend: {
              display: false // Disable the top color plate (legend)
          },
          title: {
              display: true,
              // text: 'Doughnut Chart with Labels beside Segments'
          },
          // Datalabels plugin configuration
          datalabels: {
              color: '#fff', // Label color
              anchor: 'end', // Position the label outside
              align: 'end', // Align the label beside the segments
              clamp: true, // Ensure labels stay inside the chart
              offset: 10, // Space between label and chart
              formatter: function(value, context) {
                  return context.chart.data.labels[context.dataIndex]; // Display the label next to each segment
              },
              font: {
                size: 18, // Set the font size for labels
                weight: '800' // Set the font weight for labels
            }
          }
      }
  },
  plugins: [ChartDataLabels] // Register the Datalabels plugin
});

window.Jupiter.init({
  displayMode: "integrated",
  integratedTargetId: "integrated-terminal",
  endpoint: "https://api.mainnet-beta.solana.com",
});

