 var parser = function(data) {
     var stats={}
     for (var i=0; i<=data.range*30-1; i++){
     	stats[moment().subtract(i, "days").unix()]= Math.floor(0.5 + (Math.random() * ((12 - 1) + 1)))
     }
     return stats
 }

 Template.calheatmap.rendered = function () {
 	var data = {range:1}

 	var cal = new CalHeatMap();

 	cal.init({
        data: data,
        start: moment().toDate(),
        domain: "year",
        subDomain: "day",
        legend:  [3, 6, 9, 12],
        legendVerticalPosition: "center",
        legendHorizontalPosition: "right",
        legendOrientation: "vertical",
        legendMargin: [0,0,0,20],
        legendColors: {
            min: "#d2de76",
            max: "#761d15",
            empty: "white"
        },
        range: data.range,
        itemName: ["hr", "hrs"],
        domainLabelFormat: "",
        highlight: ["now"],
        afterLoadData: parser
    });
    //cal.removeLegend();
 }

