

Template.input.events({
  'keyup #post': function(e) {
    if (e.type == "keyup" && e.which == 13 && e.ctrlKey) {
      if ($("#post").prev().hasClass("feed-element")){
        var postId = $("#post").prev().attr("id")
        _replyMessage(parseInt(postId));
      }else{
        _sendMessage();
        $("#addPost").removeClass("glyphicon-minus")
        $("#addPost").addClass("glyphicon-plus")
      }
      $("#post").hide()
    }
  }
});

Template.input.helpers({
  settings: function() {
    return {
      position: "bottom",
      limit: 5,
      rules: [
        {
          token: '@',
          collection: Meteor.users,
          field: "name",
          template: Template.userPill
        }
      ]
    };
  }
});

_getRecipients = function(msg, isReply){

  var recipients = [];

  _.each(msg.split(" "), function(v, k){
    if (v.indexOf("@")==0)
      recipients.push(v.substr(1))
  })

  if(!isReply){
    if (recipients.length)
      recipients.push(Meteor.user().username)
    else
      recipients = _.map(Meteor.users.find({}, {username:1}).fetch(), function(v, k){return v.username})
  }

  return recipients
}

_notifyUsers = function(from, recipients, _id, type) {
  _.each(recipients, function(v){
    Notifications.insert({from:from, to:v, read:false, orginId:_id, type:type})
  })
}

_sendMessage = function() {
  var el = $("#post");
  var recipients = _getRecipients(el.val(), false)

  console.log(recipients)

  feedId = 10000 + Messages.find().count({isTopic:1})

  _id = Messages.insert({user: Meteor.user().username,
                        feedId: feedId,
                        msg: el.val(), 
                        ts: moment().toDate(),
                        to: recipients
                      });

  _notifyUsers(Meteor.user().username, recipients, feedId, "message");
  //Messages.update({_id:ObjectId}, {$set:{feedId:ObjectId}})

  el.val("");

};

_replyMessage = function(postId) {
  var el = $("#post");
  var recipients = _getRecipients(el.val(), true)

  var toWho = _.union(Messages.findOne({feedId:postId}, {fields:{to:1, _id:0}}).to, recipients)
  
  console.log(toWho)

  ReplyMessages.insert({user: Meteor.user().username,
                  feedId: postId, 
                  msg: el.val(), 
                  ts: moment().toDate()
                });

  if (recipients.length){
    Meteor.call("updateNotify", postId, toWho)
  }
  _notifyUsers(Meteor.user().username, toWho, postId, "message"); 

  el.val("");
}

Template.messages.events({
  'click #addPost': function(e) {
      var plus = $("#addPost")
      if (plus.hasClass("glyphicon-plus")) {
        $(".message-status").after($("#post"))
        $("#post").show()
        plus.removeClass("glyphicon-plus")
        plus.addClass("glyphicon-minus")
        $("#post").focus()
      } else {
        $("#post").hide()
        plus.removeClass("glyphicon-minus")
        plus.addClass("glyphicon-plus")
      }
  } 
});

Template.messages.helpers({
  messages: function() {
   
    if(Session.get("todoview")){
       todoviews = Session.get("todoview")
      return Messages.find({_id:{$in:todoviews}}).fetch().concat(
              Messages.find({to:Meteor.user().username, _id:{$nin:todoviews}, ts:{"$gte":moment().startOf('day').toDate()}}, {sort: {ts: -1}}).fetch())
    }
    else
      return Messages.find({to:Meteor.user().username, ts:{"$gte":moment().startOf('day').toDate()}}, {sort: {ts: -1}})

  },
  notifycnt: function(){
    return Notifications.find({to:Meteor.user().username,
                              from:{$ne:Meteor.user().username},
                              read:false}).count();
  }
});

Template.message.created = function(){
  this.editable = new ReactiveVar(false);
}

Template.message.events({
  'click .replyto': function(e) {
      var post = $(e.target).parents("div.feed-element")
      post.after($("#post"))
      $("#post").show()
      $("#post").focus()
  },
  'click div.feed-element.unread': function(e){
      Meteor.call("updateNotifyRead", this.feedId, Meteor.user().username)
      //$(e.target).removeClass("unread")
  },
  'click .glyphicon-tasks':function(e){

        parentdom = $(e.target).parents("div.todobar")[0]

        if($(e.target).hasClass("edit")){

          //update todo list
          var task = $("#todonew").val()
          due = moment($("#eta").val() + " 18:00:00", "DD/MM/YYYY HH:mm:ss")

          feedId = $(e.target).parents("div.feed-element").attr("id")
          if (this.istodo)
            Messages.update({_id:this._id}, {$set:{taskname: task, eta:due.toDate(), status:"updated"}})
          else
            Messages.update({_id:this._id}, {$set:{taskname: task, todots: moment().toDate(), eta:due.toDate(), status:"new", istodo:true}})

          Template.instance().editable.set(false)
          $(e.target).removeClass("edit")
        }else{
          Template.instance().editable.set(true)
          $(e.target).addClass("edit")
        }
  }
})

Template.message.helpers({
  timestamp: function(){
    return moment(this.ts).format("h:mm:ss a");
  },
  unread: function(){
    return Notifications.findOne({orginId:this.feedId, 
                                  to:Meteor.user().username,
                                  from:{$ne:Meteor.user().username},
                                  read:false}) ? true : false
  },
  editable:function(){
    return Template.instance().editable.get() 
  },
  tododata:function(){
    return _.extend({"taskname":this.taskname}, _todoPiety(moment(this.ts), moment(this.eta)))
  },
  replies: function(){
    return ReplyMessages.find({feedId:this.feedId}, {sort:{ts:1}})
  },
  alias: function(){
    u = Meteor.users.findOne({username:this.user})
    return u.name?u.name:u.username
  },
  avatar: function(){
    u = Meteor.users.findOne({username:this.user})
    return u.name?u.username:"dummy"
  }
});

Template.reply.helpers({
  timestamp: function(){
    return moment(this.ts).from(moment(this.topic_ts)).replace("ago", "later");
  },
  alias: function(){
    u = Meteor.users.findOne({username:this.user})
    return u.name?u.name:u.username
  },
  avatar: function(){
    u = Meteor.users.findOne({username:this.user})
    return u.name?u.username:"dummy"
  }
})
