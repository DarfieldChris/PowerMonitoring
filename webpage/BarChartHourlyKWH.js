function BarChartHourlyKWH(placeholder, cfg)
{
   this.Logger = Logger.get('BarChartHourlyKWH');
   this.placeholder = placeholder;
   this.cfg = cfg;

   // Setup storage for the database query variables
   //    - setup as an array ob objects so that you
   //      can navigate queries like a webpage
   this.DBQ = [{}];
   
   // this is used by hosting page to change viewed data
   this.DBQ_UI = {};
    
   // set the initial start/end date for the viewed consumption data
   //     We will start by dispaying the last 7 days of data ...
   //     To do this we need a start date and an end date.
   var curr = new Date();
   var last = curr.getDate();
   var first = last - 10;
   var firstDate = new Date(curr.setDate(first));
   //var lastDate = new Date(curr.setDate(last));
   var lastDate = new Date();
   this.DBQ[0].date_Start = firstDate.getFullYear() + '-' + (firstDate.getMonth()+1) + '-' + firstDate.getDate();
   this.DBQ[0].date_End = lastDate.getFullYear() + '-' + (lastDate.getMonth()+1) + '-' + lastDate.getDate();

   // set a comparison date so that the consumption data can be compared to another date range
   //window.wpd3.compare = "-1 month";
   this.DBQ[0].compare = "";

   // set the time interval of the returned data (hour, day, month, year)
   this.DBQ[0].interval = "day";

   // select circuits to display
   //this.DBQ[0].circuits = {"8568062": true};
   //this.DBQ[0].circuits = {"8568062": true, "HWT": true};
   //this.DBQ[0].circuits = {"HWT"};
   this.DBQ[0].circuits = {};
      
   // Parse or format the date / time
   this.stringDate = "%Y-%m-%d";
   this.formatDate = d3.time.format(this.stringDate);
   this.parseDate = d3.time.format(this.stringDate + " %H:%M:%S").parse;

   // Set the dimensions of the canvas / graph
   this.margin = {top: 30, right: 150, bottom: 100, left: 75};
   this.width = this.cfg.width - this.margin.left - this.margin.right,
   this.height = this.cfg.height - this.margin.top - this.margin.bottom;

//    this.title = function title() {
//        return "Power Consumption starting on " + this.DBQ[0].date_Start + "(plotted every " + this.DBQ[0].interval + ")";
//    };

   this.newDatabaseQuery = function (_this) { 
          res = {};
          res.date_Start = _this.DBQ_UI.date_Start;
          res.date_End = _this.DBQ_UI.date_End;
          res.interval = _this.DBQ_UI.interval;
          res.compare = _this.DBQ_UI.compare;
          res.circuits = _this.DBQ_UI.circuits;
          _this.DBQ.unshift(res);

          _this.refresh([], _this);
   };


// Function to figure out the php request to use for the chart data
this.dfile = function dfile() {
    var res = this.cfg.PHP_SQL + "?date_start=" + this.DBQ[0].date_Start + "&date_end=" + this.DBQ[0].date_End + "&interval=" + this.DBQ[0].interval;

    var _keys = Object.keys(this.DBQ[0].circuits);
    if (_keys.length > 0 )
    {
        res = res + "&circuits=" + _keys.join();
    }
    if (this.DBQ[0].compare && this.DBQ[0].compare !== "" )
    {
        res = res + "&compare_to=" + this.DBQ[0].compare;
    }

    return res;
};

// Function to select date/time formatting of x-axis ticks
this.formatTicks = function formatTicks() {
    if ( this.DBQ[0].interval == "year") {
        return "%Y";
    } else if (this.DBQ[0].interval == "month") {
        return "%b %y";
    } else if (this.DBQ[0].interval == "day") {
        return "%b %d";
    } else if (this.DBQ[0].interval == "hour") {
        return "%a:%H";
    }
    return "%y-%m-%d %H";
};


this.estimateTimeInterval = function estimateTimeInterval(_start, _end, _this) {
    var sd = d3.time.format(_this.stringDate).parse(_start);
    var ed = d3.time.format(_this.stringDate).parse(_end);

    var t = ed.getTime() - sd.getTime();
    var days = t/(1000*60*60*24);
    var res = "hour";

    _this.Logger.debug(arguments.callee.name + ": " + days +" (" + t + ")");

    if ( days > 365*1.5) {
        res = "year";
    } else if (days > 45) {
        res = "month";
    } else if (days > 1 ) {
        res = "day";
    }

    return res;
};


this.newDBQ = function newDBQ(_this) {
    res = {};
    res.circuits = _this.DBQ[0].circuits;
    res.compare = _this.DBQ[0].compare;
    res.interval = _this.DBQ[0].interval;
    res.date_Start = _this.DBQ[0].date_Start;
    res.date_End = _this.DBQ[0].date_End;

    return res;
};

// Function to figure out drill-down interval and date range from:
//      - _inter: the existing interval
//      - _date: an existing date
this.newInterval = function newInterval(_inter, _date, _this) {
    _this.Logger.debug(arguments.callee.name + ": " + _inter + " Date: " + _date);

    res = _this.newDBQ(_this);
    res.date_Start = _this.formatDate(_date);
    if ( _inter == "year") {
        res.interval = "month";
        copy = new Date(_date.getFullYear() + 1, 0, 0);
        res.date_End = _this.formatDate(copy);
    } else if (_inter == "month") {
        res.interval = "day";
        copy = new Date(_date.getFullYear(), _date.getMonth()+1, 0);
        res.date_End = _this.formatDate(copy);
    } else if (_this.DBQ[0].interval == "day") {
        res.interval = "hour";
        res.date_End = _this.formatDate(_date);
    } else {
        res = null;
    }
    return res;
};

this.update = function update(_idlist, _this)
{
}

this.redraw = function redraw(data, _this)
{
    _this.x.domain(data.map(function(d) { return d.DATE_TIME; }));
    _this.y.domain([0, d3.max(data, function(d) { return d.POWER_KWH; })]);

    _this.xAxis.tickFormat(d3.time.format(_this.formatTicks()));

    var svg = d3.select("#" + _this.placeholder).transition();

    svg.selectAll(".legend").remove();
    svg.selectAll(".legendToggle").remove();
    svg.selectAll("bar").remove();
    svg.selectAll("rect").remove();
    //svg.select(".x.axis").selectAll(".text").remove();
    svg.select(".x.axis").duration(750).call(_this.xAxis)
     .selectAll("text")
      .style("text-anchor", "end")
      .attr("dx", "-.8em")
//      .attr("dy", "-.55em")
      .attr("dy", "-.3em")
      .attr("transform", "rotate(-90)" );
      
    svg.select(".y.axis").duration(750).call(_this.yAxis);
    //svg.select("#" + _this.placeholder + "Title").duration(200).text(_this.title());

    var dataNest = d3.nest()
        .key(function(d) {return d.CIRCUIT;})
        .entries(data);    // Add the valueline path.
        
    var slice = _this.x.rangeBand()/dataNest.length;        
    var legendSpace = _this.width/dataNest.length;
    
    // Loop through each symbol / key
    dataNest.forEach(function(d,i) {

        // Do we know about this circuit?
        mqtt.validateCircuit(d.key);

        if ( typeof _this.DBQ[0].circuits[d.key] === "undefined" ) {
            _this.DBQ[0].circuits[d.key] = true;
        }

        if (_this.DBQ[0].circuits[d.key] ) {
          d3.select("#" + _this.placeholder + "_canvas").selectAll("bar")
            .data(d.values)
            .enter().append("rect")
            .attr("id", _this.placeholder)
            .attr("class", _this.placeholder + "_" + d.key)
            .style("stroke", function() {
                return d.color = "black"; //_this.cfg.color(d.key); 
            })
            .style("fill", function() {
                return d.color = _this.cfg.color(d.key); })
            .attr("x", function(d) {
                if (_this.DBQ[0].compare!=="") {
                    return _this.x(d.DATE_TIME) + i*slice;
                } else {
                    if (d.totals_column)
                    {
                        return _this.x(d.DATE_TIME);
                    }
                    else
                    {
                        return _this.x(d.DATE_TIME) + 3;
                    }
                }
            })
            .attr("width", _this.x.rangeBand()/(_this.DBQ[0].compare!==""?dataNest.length:1))
            .attr("y", function(d) { return _this.y(d.y_offset); })
            .attr("height", function(d) { return _this.height - _this.y(d.POWER_KWH); })
        .on("click", function(d){
            _this = window.wpd3.tabs[d3.event.target.id];
            _this.Logger.debug ("CLICK ...");
            res = _this.newInterval(_this.DBQ[0].interval, d.DATE_TIME, _this);
            if ( res !== null) {
                _this.DBQ.unshift(res);
                _this.refresh(Object.keys(_this.DBQ[0].circuits), _this);
            }
        })
        .on("mouseover", function(d) {
            _this = window.wpd3.tabs[d3.event.target.id];
            _this.div.transition()		
                .duration(200)		
                .style("opacity", .9);		
            _this.div
                .html(d3.time.format(_this.formatTicks())(d.DATE_TIME) + "<br/>" + _this.cfg[d.CIRCUIT].title + "<br/>"  + (Math.round(d.POWER_KWH * 10) / 10.0) + "kW-hrs")	
                .style("left", (d3.event.pageX) + "px")		
                .style("top", (d3.event.pageY - 28) + "px");
            })					
        .on("mouseout", function(d) {		
            _this = window.wpd3.tabs[d3.event.target.id];		
            _this.div.transition()		
                .duration(500)		
                .style("opacity", 0);	
        });
        }
     
        d3.select("#" + _this.placeholder + "_canvas")
          .append("text")
            //.attr("x", (legendSpace/10)+i*legendSpace)
            .attr("x", (_this.width + 15))
            //.attr("y", _this.height + _this.margin.bottom)
            .attr("y", ((2*i+.5).toString())+"em")
            .attr("dy", "-1em")
            .attr("class", "legend")    // style the legend
            .style("fill", function() { // dynamic colours
                return d.color = _this.cfg.color(d.key); })
            .text(_this.cfg[d.key].title);

        d3.select("#" + _this.placeholder + "_canvas")
          .append("text")
            .attr("x", (_this.width + 25))
            .attr("y", ((2*i+1.5).toString())+"em")
            .attr("dy", "-1em")
            .attr("class", "legend")    // style the legend
            .style("fill", function() { // dynamic colours
                return d.color = _this.cfg.color(d.key); })
            .text((Math.round(_this.totals[d.key]*10)/10.0) + " kwh");

        //_this.svg
        d3.select("#" + _this.placeholder + "_canvas")
            .append("circle")
                    .attr("id", _this.placeholder + "_" + d.key )
                    .attr("cx", (_this.width+5))
                    //.attr("cx", (legendSpace/10)+i*legendSpace)
                    .attr("cy", ((2*i-.8).toString())+"em")
                    //.attr("cy", _this.height)
                    .attr("stroke", "black")
                    .attr("stroke-width","2")
                    .attr("r", 5)
                    .attr("class", "legendToggle")    // style the legend
                    .on("click", _this.toggleVisible)
                    .style("fill", function() { // dynamic colours
                        return (_this.DBQ[0].circuits[d.key] == false) ? "white" : d.color = _this.cfg.color(d.key); 
                    });
    });
}

// Function to update the chart after the datasets have changed
this.refresh = function refresh(_idlist, _this) {
  if (_this == 'undefined') {
     _this = this;
  }
  _this.Logger.debug(arguments.callee.name + ": " + _this.dfile());

  if (_this.DBQ.length > 1)
  {
      $('#' + _this.placeholder + "_back").prop('disabled', false);
      //$('#' + _this.placeholder + "_back").show();
  } else {
      $('#' + _this.placeholder + "_back").prop('disabled', true);
      //$('#' + _this.placeholder + "_back").hide();
  }

  _this.totals = {};
  
  d3.json(_this.dfile(), function(error, data) {
    data.forEach(function(d,j) {
        d.DATE_TIME = _this.parseDate(d.DATE_TIME);
        d.POWER_KWH = +d.POWER_KWH;
        if (typeof _this.totals[d.CIRCUIT] == 'undefined' ) _this.totals[d.CIRCUIT] = 0;
        _this.totals[d.CIRCUIT] = _this.totals[d.CIRCUIT] + d.POWER_KWH;
    });

    // go through the datasets by time interval and stack the power readings
    var dataStack = d3.nest()
        .key(function(d) {return d.DATE_TIME;})
        .entries(data);
    dataStack.forEach(function(d,i) {
        // UGLY - check to see if first column is
        // stacked is hard coded - CSN
        _this.Logger.debug(d.values[0].CIRCUIT + " not_stacked =" + _this.cfg[d.values[0].CIRCUIT].not_stacked);
        if (_this.cfg[d.values[0].CIRCUIT].not_stacked === true)
        {
            d.values[0].totals_column = 1;
        }
        else
        {
            d.values[0].totals_column = 0;
        }
        
        for (var j = 0; j < d.values.length; j++) {
            d.values[j].y_offset = d.values[j].POWER_KWH;
            
            if (_this.DBQ[0].compare==="" && j > d.values[0].totals_column )
            {
                d.values[j].y_offset += d.values[j-1].y_offset;
            }
        }       
    });

    _this.data = data;
    _this.redraw(data, _this);

  });

  // UGLY - update UI elements on hosting page
  try {
      document.getElementById(_this.placeholder + "_fromDate").value = _this.DBQ[0].date_Start;
      jQuery( "#" + _this._placeholder + "_fromDate" ).datepicker( "option", "maxDate",  _this.DBQ[0].date_End);
      document.getElementById(_this.placeholder + "_toDate").value = this.DBQ[0].date_End;
      jQuery( "#" + _this._placeholder + "_toDate" ).datepicker( "option", "minDate",  _this.DBQ[0].date_Start);
      document.getElementById(_this.placeholder + "_intervalScale").value = _this.DBQ[0].interval;
  //document.getElementById("compareDate").value = this.DBQ[0].compare;
  } catch (err) {
      _this.Logger.warn(arguments.callee.name + ": Failed to update UI elements");
  }
  _this.DBQ_UI.date_Start = _this.DBQ[0].date_Start;
  _this.DBQ_UI.date_End = _this.DBQ[0].date_End;
  _this.DBQ_UI.interval = _this.DBQ[0].interval;
  _this.DBQ_UI.compare = _this.DBQ[0].compare;
  _this.DBQ_UI.circuits = _this.DBQ[0].circuits;
};

this.x = d3.scale.ordinal().rangeRoundBands([0, this.width], .08);

this.y = d3.scale.linear().range([this.height, 0]);

this.xAxis = d3.svg.axis()
    .scale(this.x)
    .orient("bottom")
    .tickFormat(d3.time.format(this.formatTicks()));

this.yAxis = d3.svg.axis()
    .scale(this.y)
    .orient("left")
    .ticks(10);

this.div = d3.select("#" + this.placeholder).append("div")	
    .attr("class", "tooltip")				
    .style("opacity", 0);

this.svg = d3.select("#" + this.placeholder).append("svg")
    .attr("width", this.width + this.margin.left + this.margin.right)
    .attr("height", this.height + this.margin.top + this.margin.bottom)
  .append("g")
    .attr("width", this.width)
    .attr("height", this.height)
    .attr("transform", 
          "translate(" + this.margin.left + "," + this.margin.top + ")")
    .attr("id", this.placeholder + "_canvas");

this.svg.append("g")
      .attr("class", "x axis")
      //.attr("width", this.width)
      .attr("transform", "translate(0," + this.height + ")")
      .call(this.xAxis);

this.svg.append("g")
      .attr("class", "y axis")
      .call(this.yAxis)
    .append("text")
        .attr("transform", "rotate(-90)")
        .attr("y", 0 + (-1)*this.margin.left)
        .attr("x",0 - (this.height / 2))
        .attr("dy", "1em")
        .style("text-anchor", "middle")
        .text("kW-hours");
        
// Add a title to the graph
/*
this.svg.append("text")
        //.attr("id", this.placeholder)
        .attr("x", (this.width / 2))				
        .attr("y", 0 - (this.margin.top / 2))
        .attr("text-anchor", "middle")	
        .attr("id", this.placeholder + "_Title")
        .style("font-size", "16px") 
        .style("text-decoration", "underline") 	
        .text(this.title())
        .on("click", function(d){
            _placeholder = (d3.event.target.id).split("_");
            _placeholder = _placeholder[0];
            _this = window.wpd3.tabs[_placeholder];
            _this.Logger.debug("Clicked " + d3.event.target.id);
            if (_this.DBQ.length > 1 ) {
                _this.DBQ.shift();
                _this.refresh(Object.keys(_this.DBQ[0].circuits), _this);
            }
        });
 */

        // Setup the HTML  UI elements
       jQuery('#' + this.placeholder + '_fromDate').datepicker({
           id: this.placeholder + "_fromDateDatePicker",
           dateFormat : 'yy-mm-dd',
           onClose: function( selectedDate, dp ) {
              var _target =  $(this).attr("id");
              var _target = _target.split("_");
              var _placeholder = _target[0];

              jQuery( "#" + _placeholder + "_toDate" ).datepicker( "option", "minDate", selectedDate );

              var _this = window.wpd3.tabs[_placeholder];
              _this.DBQ_UI.date_Start = selectedDate;
              _this.Logger.debug("From " + _placeholder + " " + selectedDate);
              _this.DBQ_UI.interval = _this.estimateTimeInterval(_this.DBQ_UI.date_Start,_this.DBQ_UI.date_End, _this);
              _this.newDatabaseQuery(_this);
          }
       });

       jQuery('#' + this.placeholder + '_toDate').datepicker({
           dateFormat : 'yy-mm-dd',
           onClose: function( selectedDate ) {
              var _target = $(this).attr("id");
              var _target = _target.split("_");
              var _placeholder = _target[0];

              jQuery( "#" + _placeholder + "_fromDate" ).datepicker( "option", "maxDate", selectedDate );
              var _this = window.wpd3.tabs[_placeholder];
              _this.DBQ_UI.date_End = selectedDate;
              _this.Logger.debug("To " + _placeholder + " " + selectedDate);
               _this.DBQ_UI.interval = _this.estimateTimeInterval(_this.DBQ_UI.date_Start,_this.DBQ_UI.date_End, _this);

              _this.newDatabaseQuery(_this);
          }
       });

       document.getElementById(this.placeholder + "_intervalScale").onchange = function () {
              var _target = $(this).attr("id");
              var _target = _target.split("_");
              var _placeholder = _target[0];
              var _this = window.wpd3.tabs[_placeholder];
              _this.DBQ_UI.interval = event.currentTarget.options[event.currentTarget.selectedIndex].value;
              _this.Logger.debug("Interval " + _placeholder + " " + _this.DBQ_UI.interval);
              _this.newDatabaseQuery(_this);
       };


       document.getElementById(this.placeholder + "_back").onclick = function () {
              var _target = $(this).attr("id");
              var _target = _target.split("_");
              var _placeholder = _target[0];
              var _this = window.wpd3.tabs[_placeholder];

              if (_this.DBQ.length > 1 )
              {
                  _this.DBQ.shift();
                  _this.refresh([], _this);
              }
       };

       document.getElementById(this.placeholder + "_compareDate").onclick = function () {
              var _target = $(this).attr("id");
              var _target = _target.split("_");
              var _placeholder = _target[0];
              var _this = window.wpd3.tabs[_placeholder];

              var cmp = event.currentTarget.options[event.currentTarget.selectedIndex].value;

              // can only compare against one circuit ... use the first visible one
              (Object.keys(_this.DBQ[0].circuits)).forEach(function (key) {
                  if (_this.DBQ[0].circuits[key] === true) {
                      res = _this.newDBQ(_this);
                      res.circuits = {};
                      res.circuits[key] = true;
                      res.compare = cmp;
                      _this.DBQ.unshift(res);
                      _this.refresh([], _this);
                      return;
                  }
              });
       };


       this.toggleVisible = function toggleVisible() {
           var _target = d3.event.target.id;
           var _target = d3.event.target.id.split("_");
           var _id = _target[1];
           var _placeholder = _target[0];

           // HACK - NOT SURE HOW TO DO THIS FROM EVENT? - CSN
           _this = window.wpd3.tabs[_placeholder];

           _this.Logger.debug("%s: click ... %s", arguments.callee.name, _id + ":" + _placeholder);

           _this.DBQ[0].circuits[_id] = !(_this.DBQ[0].circuits[_id]);
           _this.redraw(_this.data, _this);
       }

       this.refresh(Object.keys(this.DBQ[0].circuits), this);
}