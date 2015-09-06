var menusData = [
  {
    location: 'Tokyo',
    snapshots: [
      {
        name: 'jpyclose',
        eta: '7:30',
        offset: -1
      },
      {
        name: 'ccyclose',
        eta: '10:30',
        offset: 0        
      },
      {
        name: 'ccymorning',
        eta: '11:30',
        offset: 0
      }
    ]
  }, 
  {
    location: 'London',
    snapshots: [
      {
        name: 'eurevening',
        eta: '7:30',
        offset: -1
      },
      {
        name: 'eurclose',
        eta: '11:30',
        offset: -1        
      },
      {
        name: 'europen',
        eta: '12:30',
        offset: -1
      }
    ]
  }
];

var dummyusers = [
  {profile: { name: 'Ren Wei', username:'archlight'}},
  {profile: { name: 'Martin', username:'martin'}},
  {profile: { name: 'Henri Hay', username:'henri'}},
  {profile: { name: 'Ivan', username:'ivan'}}
]

Meteor.methods({
  "updateNotify":function(feedId, toWho){
    Messages.update({feedId:feedId}, {$set:{to:toWho}})
  },
  "updateNotifyRead":function(feedId, toWho){
    Notifications.update({orginId:feedId, to:toWho}, {$set:{read:true}},{multi:true})
  },
  "rebuildindex":function(){
    sts = Meteor.http.post("http://localhost:8080/interstellar/rebuildindex")
    Meteor._debug("rebuild complete")
    return "OK"
  },
  "rampdiff":function(postparams){
    return Meteor.http.post("http://localhost:8080/interstellar/rampdiff",{params: postparams})
  },
  //reserved for on-demand query old fashion way
  "dealsFailed":function(){
    result = Meteor.http.get("http://localhost:8888")
    if(result.statusCode==200) {
      var respJson = JSON.parse(result.content);
      console.log("response received.");
      return respJson;
    } else {
      console.log("Response issue: ", result.statusCode);
      var errorJson = JSON.parse(result.content);
      throw new Meteor.Error(result.statusCode, errorJson.error);
    }
  }
})


if (Menus.find().count() ==0){
    _.each(menusData, function(v){
    	Menus.insert(v);
    })
}

Meteor.publish('userData', function(){
  //Meteor._debug("subscribed")
  return Meteor.users.find({},{fields:{username:1, name:1}})
});

Meteor.publish('menus', function() {
  //Meteor._debug("subscribed")
  return Menus.find({}); 
});

Meteor.publish('jobqueue', function() {
  return Jobqueue.find({BASE_DT:{"$gte":moment().add(-7, "days").toDate()}}); 
});

Meteor.publish('errors', function(options) {
  return Errors.find({}, options); 
});

Meteor.publish('errtemplate', function() {
  return Errtemplate.find({}); 
});

Meteor.publish('messages', function(u) {
  return Messages.find({}, {to:u?u.username:""});
});

Meteor.publish('replymessages', function() {
  return ReplyMessages.find({});
});

Meteor.publish('notifications', function() {
  return Notifications.find({});
});

Meteor.publish('quotes', function() {
  return Quotes.find({},{sort: {updatetime: -1}, limit:58});
});

Meteor.publish('solution', function() {
  return Solution.find({});
});

Meteor.publish('activity', function() {
  return Activity.find({});
});

Meteor.publish('rrqueue', function() {
  return Rrqueue.find({});
});

Meteor.publish('scheduler', function() {
  return Scheduler.find({});
});

Meteor.publish('todolist', function() {
  return Todolist.find({});
});

//clear Messages
//Messages.remove({});