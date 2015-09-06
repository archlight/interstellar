Template.mainview.helpers({
	locations: function(){
		return [{"name":"Tokyo"}, {"name":"London"}]
	}
});

Template.preview.helpers({
    snapshots: function(){
        return Menus.findOne({location:this.name}).snapshots;
    }   
});

Template.preview.events({
  'click a':function(e){
    scene = $(e.target).text()
    console.log(scene)
    Session.set("scene",scene)    
  }
})

Template.intraday.helpers({
  activity:function(){
    return _.map(Activity.find({"start_time":{"$gte":moment().startOf('day').toDate()}, "user":Meteor.user().username.toUpperCase()}).fetch(), function(v, k){
      return {"session_id":v.session_id, "rrqueue":Rrqueue.find({"session_id":v.session_id})}
    })
  }
})

Template.intradayjob.helpers({
  percent:function(){ 
    if(this.sts_cod=="OK" || this.sts_cod=="KO")
      progress = 100
    else
      progress = Math.floor(0, this.progress*100-2)
    return progress
  },
  status:function(){
    if(this.sts_cod=="OK" || this.sts_cod=="KO")
      return this.progress == 0?"progress-bar-danger":"progress-bar-success"
    else
      return "progress-bar-info"
  }

})

// Template.quotes.rendered = function(){
//   this.autorun(function(){
//     var width = 400
//     var height = 50
//     var padding = 10

//     console.info(moment().format())
//     console.info(Session.get("autorun"))
//     var numseries = series.length

//     var central = this.reference
//     var yscale = d3.scale.linear().range([central*0.95, central*1.05]);

//     var svg = d3.select("#sparkline")
//               .append("svg")
//               .attr("width", width)
//               .attr("height", height);

//     svg.selectAll("rect")
//        .data(series)
//        .enter()
//        .append("rect")
//        .attr("x", function(d, i){ return i*(width/numseries)+(width/numseries - padding)/2})
//        .attr("y", function(d){return yscale(d)})
//        .attr("width", 20)
//        .attr("height", 100);
//    })
// }

function _variation(recent, previous){

  diff = recent-previous
  if (Math.abs(diff) > 0.00001){
    num = (""+diff).split(".")
    recent = ""+recent
    if (parseInt(num[0])){
      idx = recent.indexOf(".")-num[0].length
      return [recent.slice(0, idx), recent.slice(idx)]
    }else{
      for(i=0;i<num[1].length;i++)
        if(parseInt(num[1][i])>0){
          idx = i+1
          break
        }
      idx = recent.indexOf(".") + idx
      return [recent.slice(0, idx), recent.slice(idx)] 
    }
  }else{
    return [recent, ""]
  }
}

Template.quotes.helpers({
  quotes: function(){
      s = _.groupBy(Quotes.find({}, {sort:{QuoteId:1}}).fetch(), function(v, k){return v.QuoteGroup})
      return _.map(s, function(val,k){
        data = []
        _.each(_.groupBy(val, function(v, k){return v.Quote}), function(v, k){
          recent = v[0]
          previous = v.length>1?v[1]:v[0]
          decimal = recent.LIVE>0.1?2:4
          change = _variation(recent.LIVE.toFixed(decimal), previous.LIVE.toFixed(decimal))
          updown = recent.LIVE-previous.LIVE>0?"up":"down"
          chg = updown=="up"?"+"+recent.Change.toFixed(decimal):""+recent.Change.toFixed(decimal)
          data.push({"quote":k, "instr":recent.QuoteType, "changed":change[1], "unchanged":change[0], "updown": updown, "official":recent.OFFICIAL.toFixed(decimal), "change":chg, "data":v})
        })
        return {"quotegroup":k, "data":data}
      })
  }
})

Template.quotes.rendered = function(){
  Tracker.autorun(function(){
    if (Quotes.find().count()){
      setTimeout(function(){$(".update").removeClass('up'); $(".update").removeClass('down')}, 1000)}
  })
}