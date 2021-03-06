mqtt = { 
    //host:  '216.57.180.140',	// hostname or IP address
    host:  '192.168.1.121',	// hostname or IP address
    port:  7681,
    topic: 'PMon/TDE',	                // topic to subscribe to
    useTLS:false,
    username: null,
    password: null,
    // username = "jjolie",
    // password = "aa",
    cleansession: true,
    reconnectTimeout: 5000,
    //reconnectTimeout: 60000,
};



window.wpd3 = {
    idlist: [],
    tabs:   {},

    // basic window size we are working with
    width: Math.min(window.innerWidth - 50, 900),
    height: Math.min(window.innerHeight, 400),

    // setup colors for the data sets
    color: d3.scale.category10(),

    // database server for historical kwh HTTP requests
    PHP_SQL: "http://www.darfieldearthship.com/data.php",
 
    // Define circuits we might be looking at ...
    '8568062': {
        title:   "Total Residential",
        subtitle:"kwatts",
        ranges: [3,6,9],
        not_stacked: true,
    },

    HWT: {
        title:   "Hot Water Tank",
        subtitle:"kwatts",
        ranges: [3,6,9],
    },

    STOVE: {
        title:   "Electric Stove",
        subtitle:"kwatts",
        ranges: [3,6,9],
    },

    config_gauge: {
	size: 200,
	label: "CONSUMPTION",
	min: 0,
	max: 9,
	minorTicks: 3,
        majorTicks: 4,
        greenZones: [{ from: 0, to: 3 }],
        yellowZones: [{ from: 3, to: 6 }],
        redZones: [{ from: 6, to: 9}],
    },
};

// Logging

// taken from ???
var invokeConsoleMethod = function (hdlr, messages) {
	Function.prototype.apply.call(hdlr, console, messages);
};

function _myHandler(messages, context) {
        var hdlr = console.log;
        var msg = "[";

	// Prepend the logger's name to the log message for easy identification.
	if (context.name ) {
		msg = msg + context.name + ":";
	}
        messages[0] = msg + context.level.name + "] " + messages[0];

	if (context.level === Logger.TIME) {
		if (messages[1] === 'start') {
			if (console.time) {
				console.time(messages[0]);
			}
			else {
				timerStartTimeByLabelMap[messages[0]] = new Date().getTime();
			}
		}
		else {
			if (console.timeEnd) {
				console.timeEnd(messages[0]);
			}
			else {
				invokeConsoleMethod(hdlr, [ messages[0] + ': ' +
					(new Date().getTime() - timerStartTimeByLabelMap[messages[0]]) + 'ms' ]);
			}
		}
	}
	else {
		// Delegate through to custom warn/error loggers if present on the console.
		if (context.level === Logger.WARN && console.warn) {
			hdlr = console.warn;
		} else if (context.level === Logger.ERROR && console.error) {
			hdlr = console.error;
		} else if (context.level === Logger.INFO && console.info) {
			hdlr = console.info;
		}

		invokeConsoleMethod(hdlr, messages);
	}
}
Logger.setHandler(_myHandler);


// Log level can be one of:
//  - DEBUG
//  - INFO
//  - WARN
//  - ERROR
Logger.setLevel(Logger.DEBUG);

