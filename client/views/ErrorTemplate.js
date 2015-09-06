Template.ErrorTemplate.helpers({
  'errtemplate':function(){
  	return Errtemplate.find({})
  }
})

Template.ErrorTemplate.events({
  'click #btn-add':function(e){
  	Errtemplate.insert({"TYPE":$("#type").val(), "REGEXPR":$("#regexpr").val()})
  	return false    
  },
  'click #btn-rebuild':function(e){
    Meteor.call("rebuildindex", function(error, result){
        $("#buildstatus").text(result)
    })
    $("#buildstatus").text("Rebuilding")
    return false    
  },
  'click .glyphicon-remove':function(e){
  	Errtemplate.remove({"_id":this._id})
  }
})