mqtt.Logger = Logger.get('mqtt');

mqtt.update = function update(_idlist, _this) {
};

mqtt.connected = false;

mqtt.keepAliveCnt=55;

mqtt.connect = function connect() {
        var msg = "Trying to connect ... " + mqtt.host +':' + mqtt.port;
	mqtt.updateStatus("info", arguments.callee.name, msg, "images/transfer.jpeg");
	    				
        mqtt.connection = new Paho.MQTT.Client(
                        mqtt.host,
                        mqtt.port,
                        "web_" + parseInt(Math.random() * 100,
                        10));
        mqtt.connection.connected = false;

        var options = {
            timeout: 3,
            useSSL: mqtt.useTLS,
            cleanSession: mqtt.cleansession,
            onSuccess: mqtt.onSuccess,
            onFailure: function onFailure (message) {
                mqtt.connected = false;
                mqtt.connection.connected = false;

                var msg = "Connection failed: " + message.errorMessage + ". Retrying";
                mqtt.updateStatus("warn", arguments.callee.name, msg, "images/failed.jpeg");
                //setTimeout(mqtt.connect, mqtt.reconnectTimeout);
            }
        };

        mqtt.connection.onConnectionLost = mqtt.onConnectionLost;
        mqtt.connection.onMessageArrived = mqtt.onMessageArrived;

        if (mqtt.username != null) {
            options.userName = mqtt.username;
            options.password = mqtt.password;
        }
        
        mqtt.Logger.info(arguments.callee.name + ": Will connect to MQTT server using " +
	                "Host="+ mqtt.host + 
                        ", port=" + mqtt.port + 
                        " TLS = " + mqtt.useTLS + 
                        " username=" + mqtt.username + 
                        " password=" + mqtt.password);
        mqtt.connection.connect(options);
}

mqtt.onSuccess = function onSuccess() {
        mqtt.connection.connected = true;

        var msg = 'Connected to ' + mqtt.host + ':' + mqtt.port;
        mqtt.updateStatus("info", arguments.callee.name, msg, "images/connected.jpeg");

        $('#server').val(mqtt.host);
        $('#port').val(mqtt.port);

        // Connection succeeded; subscribe to our topic
        mqtt.connection.subscribe(mqtt.topic + "_PUB/#", {qos: 0});
        $('#topic').val(mqtt.topic + "_PUB/#");
        
        try {
            mqtt.publish(mqtt.topic + "_RCV/current", '1');
        } catch (err) {
            mqtt.Logger.warn("publish() failed ... " + err);
        }
}

mqtt.publish = function publish(dest, mqtt_msg) {
    var msg = "Publishing to: " + dest + " - " + mqtt_msg;
    mqtt.updateStatus("info", arguments.callee.name, msg,"images/transfer.jpeg");
    message = new Paho.MQTT.Message(mqtt_msg);
    message.destinationName = dest;
    mqtt.connection.send(message);
};

mqtt.updateStatus = function updateStatus(lvl, src, text, img) {
        mqtt.Logger[lvl]("%s: %s", src, text);
        try {
	    $('#statusIcon').attr("src", img);
	    $('#status').val(text);
        } catch (err) {
            mqtt.Logger.warn("updateStatus() failed ... " + err);
	}
}

mqtt.onConnectionLost = function onConnectionLost(responseObject) {
        mqtt.connected = false;
        mqtt.connection.connected = false;

        //setTimeout(mqtt.connect, mqtt.reconnectTimeout);
        var msg = "connection lost (" + responseObject.errorMessage + "). Reconnecting ...";
        mqtt.updateStatus("warn", arguments.callee.name, msg, "images/failed.jpeg");
}

mqtt.onMessageArrived = function onMessageArrived(message) {
        var topic = message.destinationName;

        mqtt.Logger.debug("%s: %s - %d", arguments.callee.name, 
                         topic, message.payloadBytes.length);

        	$('#subscribedevents').prepend('<li>' + topic + ' = ' + message.payloadString + '</li>');

                var res = topic.split("/");

                // only pay attention if msg formatted properly
                if ( res.length ==3 )
                {
                    if ( res[2] === "UP" )
                    {
                        mqtt.connected = true;
                        var _msg = "Connected to client " + res[0] + "." + res[1];
                        mqtt.updateStatus("info", arguments.callee.name, _msg, "images/connected.jpeg");
                    }
                    else if ( res[2] === "DOWN" )
                    {
                        mqtt.connected = false;
                    }
                    return;
                }
                else if (res.length !== 4 ) return;

                var _id = res[res.length-2];
        	var payload = parseFloat( message.payloadString );
 
               try {
                // have we got a record for  this id?
                mqtt.validateCircuit(_id);

                var new_point = mqtt.addDataPoint(_id, new Date(), payload);

                mqtt.setNewMinMax(_id, new_point);
                }
                catch (err) {
                    mqtt.Logger.error(arguments.callee.name + "(Setup Error): " + 
                                     err + "\n" + err.stack);
                }

                mqtt.Logger.debug (arguments.callee.name + " (NEW DATA): " + 
                                  _id + ": " + new_point.val + "(" + 
                                  new_point.date + ")");
                window.wpd3.gauge.update();

                try {
                    (window.wpd3.tabs[window.wpd3.active].update)([_id], window.wpd3.tabs[window.wpd3.active]);
                }
                catch (err) {
                       mqtt.Logger.error(arguments.callee.name + "(Update Error for " + 
                                     window.wpd3.active + "): " + 
                                     err + "\n" + err.stack);
                }
                mqtt.Logger.debug("%s: %s", arguments.callee.name, "Completed");
};

mqtt.keepAlive = function keepAlive() {
    mqtt.Logger.debug(arguments.callee.name + " Connection: " + mqtt.connection.connected + " Client: " + mqtt.connected);
    if (mqtt.connected === false )
    {
        mqtt.keepAliveCnt =55;

        window.wpd3.gauge.animateNetNotify(1, mqtt.reconnectTimeout);

        if (mqtt.connection.connected === false)
        {
            mqtt.connect();
        }
    } else {
        mqtt.keepAliveCnt += 1;

        window.wpd3.gauge.endNetNotify();
    }
    // Go through the circuits and see if the circuit has 
    // received a new data point recently
    //     - if not, add a datapoint to make things look active
    if ( mqtt.keepAliveCnt > 60 )
    { 
        mqtt.Logger.debug(arguments.callee.name + " Checking for stale data ,,,");
        var _time = new Date();
        window.wpd3.idlist.forEach(function keepAliveEach (d,i) {
            mqtt.Logger.debug("%s: Checking for stale data for %s", arguments.callee.name,  d.id);

            var _index = d.data.length - 1;
            var _point = d.data[_index];
            if ( _index == 0 || d.data[_index].date.getTime() + mqtt.reconnectTimeout*mqtt.keepAliveCnt < _time.getTime() )
            {
                mqtt.Logger.debug("%s: Stale data found for %s", arguments.callee.name, d.id);

                if ( d.data[_index]._keepAlivePnt == true )
                {
                    d.data[_index].date = _time;
                }
                else
                {
                    _point = mqtt.addDataPoint(d.id, _time, d.data[_index].val);
                    _point._keepAlivePnt = true;
                }
                mqtt.setNewMinMax(d.id, _point);
            }

            (window.wpd3.tabs[window.wpd3.active].update)([d.id], window.wpd3.tabs[window.wpd3.active]);

            mqtt.Logger.debug("%s: Stale data refreshed for %s (%d)", 
                              arguments.callee.name, d.id, d.data.length);
        });

        mqtt.keepAliveCnt = 0;
    }

    // Finally ... reset the keep alive
    setTimeout(mqtt.keepAlive, mqtt.reconnectTimeout);

};

mqtt.validateCircuit = function validateCircuit(_id)
{
    // Do we know about this circuit?
    if ( typeof window.wpd3[_id] === "undefined")
    {
        // NO ... need to create it
        window.wpd3[_id] = {};
        window.wpd3[_id].title = _id;
        window.wpd3[_id].subtitle = "???";
        window.wpd3[_id].ranges = [5,10,15];
    }
};

mqtt.addDataPoint = function addDataPoint(_id, _date, _val)
{
                // create the new data point (for historical trend)
                var new_point = {};
                new_point.date = _date;
                new_point.val  = _val;

                mqtt.Logger.debug(arguments.callee.name +": " + window.wpd3[_id].id + " " + (window.wpd3[_id].id === "undefined"));
                // Even if we already have a record for the id is it initialized?
                if ( typeof window.wpd3[_id].id === "undefined" )
                {
                    window.wpd3[_id].id = _id;
                    window.wpd3[_id].visible = true;
                    window.wpd3.idlist.push(window.wpd3[_id]);
                    window.wpd3[_id].data = [];
                    window.wpd3[_id].min_max_dates = [];
                    window.wpd3[_id].max_val = 5.0;

                    window.wpd3[_id].min_max_dates[0] = new_point.date;
                    window.wpd3[_id].min_max_dates[1] = new Date(new_point.date.getTime() +1*60*1000);
                }

                // store the new data point
                window.wpd3[_id].val = _val;
                window.wpd3[_id].data.push(new_point);

                return new_point;
};

mqtt.setNewMinMax = function setNewMinMax(_id, new_point)
{
                // recalculate min and max based on new data
                if ( window.wpd3[_id].min_max_dates[0].getTime() > new_point.date.getTime() )
                {
                    window.wpd3[_id].min_max_dates[0] = new_point.date;
                }

                if ( window.wpd3[_id].min_max_dates[1].getTime() < new_point.date.getTime() )
                {
                    window.wpd3[_id].min_max_dates[1] = new Date(new_point.date.getTime() +1*60*1000);
                }

                if ( new_point.val > window.wpd3[_id].max_val )
                {
                    window.wpd3[_id].max_val = new_point.val + 5.0;
                }
};

$(window).load(function load () {

    mqtt.Logger.info("Starting mqtt window load ...");

    $('#server').val(mqtt.host);
    $('#port').val(mqtt.port);

    //window.wpd3.tabs["tab5"] = mqtt;

    mqtt.connect();

    //setTimeout(mqtt.keepAlive, mqtt.reconnectTimeout);
    setInterval(mqtt.keepAlive, mqtt.reconnectTimeout);
    mqtt.Logger.info("... Finished mqtt window load");
});
