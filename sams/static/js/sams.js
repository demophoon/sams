var Check = function(id, name, hostname, status) {
    var me = this;
    me.id = id;
    me.name = name;
    me.hostname = hostname;
    me.status = ko.observable(status);
}

var query_string_vals = [], hash;
    var q = document.URL.split('?')[1];
    if(q != undefined){
        q = q.split('&');
        for(var i = 0; i < q.length; i++){
            hash = q[i].split('=');
            vars.push(hash[1]);
            vars[hash[0]] = hash[1];
        }
}

var SamsViewModel = function() {
    var me = this;
    me.checks = ko.observableArray();
    me.sort_checks = function(status) {
        return ko.computed(function() {
            return ko.utils.arrayFilter(me.checks(), function(item) {
                return item.status() == status;
            });
        });
    }
    me.up_checks = me.sort_checks("up");
    me.down_checks = me.sort_checks("down");
    me.unconfirmed_checks = me.sort_checks("unconfirmed_down");

    me.sams_status = ko.computed(function() {
        if (me.down_checks().length > 0) {
            if (me.down_checks().length > 3) {
                return me.down_checks().length + " checks are down.";
            } else if (me.down_checks().length == 1) {
                return me.down_checks()[0].name + " is down.";
            } else {
                var checknames = ko.utils.arrayMap(me.down_checks(), function (item) { return item.name });
                return checknames.join(", ") + " are down.";
            }
        } else if (me.unconfirmed_checks().length > 0) {
            if (me.unconfirmed_checks().length > 3) {
                return me.unconfirmed_checks().length + " checks are unconfirmed down.";
            } else if (me.unconfirmed_checks().length == 1) {
                return me.unconfirmed_checks()[0].name + " is unconfirmed down.";
            } else {
                var checknames = ko.utils.arrayMap(me.unconfirmed_checks(), function (item) { return item.name });
                return checknames.join(", ") + " are unconfirmed down.";
            }
        } else {
            return "Everything is up and running smoothly.";
        }
    });

    me.sams_css_class = ko.computed(function() {
        css_class = "sams ";
        if (me.down_checks().length > 0) {
            css_class += "down";
        } else if (me.unconfirmed_checks().length > 0) {
            css_class += "unconfirmed";
        } else {
            css_class += "up";
        }
        return css_class;
    });

    me.last_update = 0;
    me.getChecks = function() {
        if (new Date() - me.last_update < 15000) { return; }
        check_api_url = '/api/1.0/sams';
        
        if(query_string_vals['filter'] != null){
            check_api_url = '/api/1.0/sams/' + query_string_vals['filter']
        }
        me.last_update = new Date() * 1;
        $.ajax({
            url: check_api_url,
            method: 'GET',
            success: function(data) {
                me.checks(ko.utils.arrayMap(data, function(item) {
                    return new Check(item.id, item.name, item.hostname, item.status);
                }))
            },
        })
    }

    me.sock = null;
    me.timer = null;
    me.allow_ws = true;

    me.connect_to_sockjs = function() {
        if (!me.allow_ws) { return; }
        me.sock = new SockJS('/api/1.0/sams/ws');
        me.sock.onopen = function() {
            clearInterval(me.timer);
            me.getChecks();
        };
        me.sock.onmessage = function(e) {
            message = JSON.parse(e.data);
            for (var key in message.data) {
                check = ko.utils.arrayFirst(me.checks(), function(item) {
                    return item.id == key;
                });
                check.status(message.data[key]);
            }
        };
        me.sock.onclose = function() {
            setTimeout(me.upgrade, 5000);
            sock = null;
        };
    }

    me.window_active = function(e) {
        var prevType = $(this).data("prevType");
        if (prevType != e.type) {   //  reduce double fire issues
            switch (e.type) {
                case "blur":
                    me.fallback();
                    break;
                case "focus":
                    me.allow_ws = true;
                    me.upgrade();
                    break;
            }
        }
        $(this).data("prevType", e.type);
    }

    me.fallback = function() {
        if (me.sock) {
            me.allow_ws = false;
            me.sock.close();
            me.sock = null;
            me.timer = setInterval(function() {me.getChecks()}, 15000);
        }
    }

    me.upgrade = function() {
        if (me.sock) { return; }
        if (me.allow_ws) {
            me.connect_to_sockjs();
        } else {
            me.fallback();
        }
    }

    $(window).on("blur focus", me.window_active);

    me.getChecks();
    me.upgrade();
}
