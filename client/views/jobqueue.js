Template.jobqueue.helpers({
  //mongo aggregate not supported in meteor	
  // jobs: function() {
  //   aggegator = Jobqueue.aggregate([{$group:{_id:"$JOB_NAME", jobids:{$push:"$JOB_ID"}}}])
  //   if (aggregator.ok)
  //   	return aggregator.result
  // },
  // xxjobs:function(){
  // 	return _.map(function(v){return {"JOB_NAME":v}}, Jobqueue.distinct("JOB_NAME"))
  // },
  jobs: function(){

    res = []

	_.each(_.pluck(_.flatten(_.pluck(Menus.find().fetch(), 'snapshots')), 'name'), function(scene, k){
		
		tmp = {}

		tday = moment(Session.get("viewdate"), "DD-MM-YYYY").startOf('day')
		offset = scene.indexOf("ccy")<0?-1:0

	    if (tday.weekday()==1)
	      offset = offset - 2

	  	d = _.groupBy(Jobqueue.find({BASE_DT:{"$gte":tday.add(offset, "days").toDate()}, SCENE:scene}).fetch(), "JOB_NAME")
	  	m = _.map(d, function(v, k){
	  		// return {"JOB_NAME":k, "JOBCHAIN": _.map(v, function(vv, k){
	  		// 	return _.extend(vv, {"ERRCNT":Errors.find({JOB_ID:vv["JOB_ID"]}).count()})
	  		// })}
	  		return {"JOB_NAME":k, "JOBCHAIN":_.sortBy(v, "JOB_ID")}
	  	})
	    // d["data"] = _.filter(m, function(v){
	    //     return sts_code=="EX"?_.last(v["JOBCHAIN"])["STS_COD"] == "EX":_.last(v["JOBCHAIN"])["STS_COD"] != "EX" 
	    // })
	    tmp["data"] = m
	    tmp["scene"]=scene
	    res.push(tmp)
	})

    return res

  }
});

Template.filterby.rendered = function(){
  $("#viewdate").text(moment().format("DD-MM-YYYY"))
  Session.set("viewdate", $("#viewdate").text())
}

Template.filterby.events({
  'click .next':function(e){
    if (!$("li.next").hasClass("disabled")){
      var viewdate = moment($("#viewdate").text(), "DD-MM-YYYY")
      $("#viewdate").text(viewdate.add(1, "days").format("DD-MM-YYYY"))
      if (viewdate.add(2, "days")>moment())
        $("li.next").addClass("disabled")
      Session.set("viewdate", $("#viewdate").text())
    }
  },
  'click .previous':function(e){
    var viewdate = moment($("#viewdate").text(), "DD-MM-YYYY")
    $("#viewdate").text(viewdate.subtract(1, "days").format("DD-MM-YYYY"))
    $("li.previous").next().next().removeClass("disabled")
    Session.set("viewdate", $("#viewdate").text())
  }  
})

Template.jobitem.helpers({
  percent: function() {
  	lastjob = _.max(this.JOBCHAIN, function(v){return v.JOB_ID})
    return parseInt(lastjob.PROPORTION_DONE*100)
  },
  isRunning: function(){
  	lastone = _.last(this.JOBCHAIN)
  	return lastone["STS_COD"] == "EX"
  },
  status: function(){
    return lastone["STS_COD"] == "EX"?"progress-bar-info":"progress-bar-success"
  }

});

Template.eachjob.helpers({
  errcnt: function(){
    return Errors.find({JOB_ID:this.JOB_ID}).count()
    //return 0
  }
})

Template.jobitem.events({
  'click .breadcrumb a':function(e){
    Session.set("selectedJobId",$(e.target).text())    
  }
})

Template.errorview.events({
  'mouseup': function(e){
    keyword = window.getSelection().toString();
    if (keyword.length){
      $('p').unhighlight();
      $('p').highlight(keyword);
      $('#tagform #regexpr').val(keyword)
    }
  }
})

Template.scheduler.helpers({
  'schedtasks':function(){
    return Scheduler.find({})
  }
})