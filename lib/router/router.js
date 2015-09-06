Router.configure({
    layoutTemplate: 'layout',
    waitOn: function(){
        return [Meteor.subscribe('userData'),
                Meteor.subscribe('menus'),
                Meteor.subscribe('messages', Meteor.user()),
                Meteor.subscribe('notifications'),
                Meteor.subscribe('replymessages'),
                Meteor.subscribe('jobqueue'),
                Meteor.subscribe('errors'),
                Meteor.subscribe('errtemplate'),
                Meteor.subscribe('solution'),
                Meteor.subscribe('quotes'),
                Meteor.subscribe('activity'),
                Meteor.subscribe('rrqueue'),
                Meteor.subscribe('todolist')
        ];
    }
});

Router.map(function(){
    this.route('FixDeals', {
    	path: '/FixDeals',
    	loadingTemplate: 'spinner',
    	waitOn: function(){
    		return Meteor.subscribe('errors');
    	},
    	data: function(){
    		if(this.ready()){
                d = _.groupBy(Errors.find({}).fetch(), "TYPE")
                return _.map(d, function(v, k){return {"TYPE":k, "ERRORS_GROUP":v}})
    		}
    	}
    } );
    this.route('ErrorTemplate', {path: '/ErrorTemplate'});
    this.route('calheatmap', {path:'/statistics'});
    this.route('mainview', {path: '/'});
    this.route('jobqueue', {
        path: '/jobqueue/:_id?',
        loadingTemplate: 'spinner',
        waitOn: function(){
            return Meteor.subscribe('errors')
        },
        data: function(){
            return {"ERRORS":Errors.find({"JOB_ID":parseInt(this.params._id)})}
        }
    });
    this.route('scheduler', {
        path:'/scheduler',
        loadingTemplate:'spinner',
        waitOn: function(){
            return Meteor.subscribe('scheduler')
        },
        data: function(){
            if(this.ready()){
                return Scheduler.find({})
            }
        }
    })
});