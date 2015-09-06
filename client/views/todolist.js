_daysexcludeweekends = function(s, e){
    daydiff = e.diff(s, "days")
    if (daydiff<7 && e.weekday()<s.weekday())
      weekends = 1
    else
      weekends = (daydiff-daydiff%7)/7
    return daydiff - weekends*2 + 1
}

_todoPiety  = function(ts, eta){
    if (ts.format("DD/MM/YY")==eta.format("DD/MM/YY")){
      elapsed = [moment().diff(ts,"hours"), eta.diff(ts, "hours")]
      if(elapsed[0]>elapsed[1]){
        sts = "+" + (elapsed[0] - elapsed[1])+" hours"
        elapsed = [elapsed[1], elapsed[1]]
      }
      else
        sts = "-" + (elapsed[1] - elapsed[0])+" hours"
    }
    else{
      elapsed = [_daysexcludeweekends(ts, moment()), _daysexcludeweekends(ts, eta)]
      if(elapsed[0]>elapsed[1]){
        sts = "+" + (elapsed[0] - elapsed[1])+" days"
        elapsed = [elapsed[1], elapsed[1]]
      }
      else
        sts = "-" + (elapsed[1] - elapsed[0])+" days"
    }
    return {"data":elapsed, "chart":"pie", "status":sts}
}

Template.todolist.helpers({
  todoitems: function(){
  	return _.map(Messages.find({"istodo":true}).fetch(), function(v, k){
      ts = moment(v["todots"])
      eta = moment(v["eta"])

  		return _.extend({taskname:v["taskname"], todo_status:v["status"], _id:v["_id"]}, _todoPiety(ts, eta))
  	})
  }
});


Template.todoinput.rendered = function(){
  $("#eta").datepicker({
    format: "dd/mm/yyyy",
    daysOfWeekDisabled: "0,6",
    autoclose: true,
    todayHighlight: true
  });
}

Template.todoinput.helpers({
  etastamp:function(){
    return moment(this.eta).format("DD/MM/YYYY")
  }
})

Template.todoitem2.helpers({
  accepted:function(){
    return this.todo_status=="accepted"
  },
  selected:function(){
    todoview = Session.get("todoview")
    if(todoview)
      return todoview.indexOf(this._id)>=0
    else
      return false
  }
})

Template.todoitem2.events({
  'click .glyphicon-ok':function(e){
    sts = this.todo_status=="accepted"?"unaccepted":"accepted"
    Messages.update({_id:this._id}, {"$set":{"status":sts}})
  },
  'click a':function(e){
    d = Template.instance().$(".todoitem2")
    todoview = Session.get("todoview")
    if(todoview){
      if(todoview.indexOf(this._id)>=0)
        todoview.pop(this._id)
      else
        todoview.push(this._id)
    }
    else
      todoview=[this._id]
    
    Session.set("todoview", todoview)

  }
})