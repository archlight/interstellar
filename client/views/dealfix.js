Template.dealSummary.helpers({
  'errors':function(){
    d = _.groupBy(Errors.find({"CREATEDAT":{"$gt":moment().startOf('day').toDate()}}).fetch(), "TYPE")
    return _.map(d, function(v, k){
      deals = _.uniq(_.map(v, function(x) {return x["CFMN_NO"]}))
      jobids = _.uniq(_.map(v, function(x) {return x["JOB_ID"]}))

      deal = Errors.findOne({"TYPE":k, "CFMN_NO":deals[0]})

      //don't allow space in TYPE
      _id = k+moment().startOf('day').format("DDMMYYYY")

      return {"TYPE":k, "DEALS":deals, "TAGS":deal.TAGS, "JOBIDS":jobids, "errId":_id}
    })
  }
})

Template.dealerror.events({
  'click .glyphicon-wrench': function(e){
    $("#solution #datatable").empty()
    Template.instance().$(".panel-footer").toggleClass("show")
  }
})

Template.dealerror.rendered = function(){

}

Template.solutionfix.helpers({
  'solutionfix':function(){
    // t = this.errId.slice(0, this.errId.length-8)
    // return _.filter([Solution.findOne({"errId":{$regex:t}},{order:{_id:-1},limit:1}), Solution.findOne({"errId":this.errId})], function(v){
    //   if(v)
    //     return v
    // })
    return Solution.find({"errId":this.errId})
  }
})

Template.solutionfix.events({
  'click .glyphicon-ok':function(e){
    Solution.update({_id:this._id}, {"$set":{"accepted":!this.accepted}})
  }
})

Template.solution.rendered = function(){
  
  $(".datepicker").datepicker({
    format: "dd/mm/yyyy",
    daysOfWeekDisabled: "0,6",
    autoclose: true,
    todayHighlight: true
  });
}



Template.solution.events({
  'click #addSolution':function(e) {
    
    sln = []
    datatable = Template.instance().$("#datatable")
    
    $.each(datatable.find("li"), function(k, v){
      spans = $(v).find("div")
      itemname = $(spans[0]).text()
      bump = []
      $.each(spans.splice(1), function(k, vv){
        bump.push({"bumptenor":$($(vv).find("code.bumptenor")).text(), "bumpvalue":$($(vv).find("code.bumpvalue")).text()})
      })
      
      sln.push({"itemname":itemname,"bump":bump})
    })

    if (sln.length){
      doc = {}
      doc["bumpfix"] = sln
      doc["co"] = $("#solution-co input").val()
      doc["errId"] = this.errId
      doc["accepted"] = false

      Solution.insert(doc)
    }

    $("#solution #datatable").empty()
    $("#solution").toggleClass("show")

  },
  'click #GetRamp': function(e) {
    if (e.type == "click") {
      srcset = Template.instance().$("#srcset").val()
      destset = Template.instance().$("#destset").val()
      datepicker = Template.instance().$(".datepicker").val()
      param = {"baseSet":srcset, "destSet":destset, "setDate":datepicker}
      datatable = Template.instance().$("#datatable")
      console.log(param)
      Meteor.call("rampdiff", param, function(error, result){
        console.log(result)
        if (result["statusCode"]!="200"){
          $("#datatable").empty()
          $("<p></p").text(error).appendTo(datatable)
        }
        else{
          $("#datatable").empty()
          var jsObject = JSON.parse(result.content)
          console.log(jsObject)

          var ul = $("<ul></ul>").addClass("list-unstyled")
          _.each(jsObject, function(v, itemname){
              li = $("<li></li>")
              $("<div></div>").text(itemname).appendTo(li)

              _.each(JSON.parse(v[0]), function(vv, tenor){
                var line = $("<div></div>")
                $("<code></code>").addClass("bumptenor").text(tenor).appendTo(line)

                _.each(vv, function(dd, k){
                  if (dd)
                    $("<code></code>").addClass("bumpvalue").text(k+" : "+dd).appendTo(line)
                })
                
                line.appendTo(li)
              })
              li.appendTo(ul)
          })
          ul.appendTo(datatable)

          // var items=[];
          // var tbl = $("<table></table>")
          // tbl.addClass("table table-bordered")

          // $.each(data, function(k, v){
          //     if (tbl.children().length==0){
          //         var th = $("<tr></tr>")
          //         th.append("<td></td>")
          //         $.each(v, function(col, val){
          //           th.append("<td>"+col+"</td>")
          //         });
          //         th.appendTo(tbl)
          //     }
          //     var tr = $("<tr></tr>")
          //     tr.append($("<td>"+k+"</td>"))
          //     $.each(v, function(col, val){
          //       tr.append("<td>"+val+"</td>")
          //     });
          //     tr.appendTo(tbl)
          // });

          // tbl.appendTo($("#datatable"));
        }
      });
    }
  }
});