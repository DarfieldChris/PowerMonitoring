function Lines(placeholder, cfg)
{
    this.Logger = Logger.get('lines');
    this.placeholder = placeholder;
    this.cfg = cfg;

    this.min_max_dates = [(new Date()), (new Date())];
    this.max_val = 0.0;

    this.toggleVisible = function toggleVisible() {
        //var _id = new String(this.id);

        var _target = d3.event.target.id;
        var _target = _target.split(" ");
        var _id = _target[0];
        var _placeholder = _target[1];

        // HACK - NOT SURE HOW TO DO THIS FROM EVENT? - CSN
        _this = window.wpd3.tabs[_placeholder];

        _this.Logger.debug("%s: click ... %s", arguments.callee.name, _id + _placeholder);

        _this.cfg[_id].visible = !(_this.cfg[_id].visible);
        (_this.update)([_id], _this);

        _this.Logger.debug("%s: clicked ... %s", arguments.callee.name, _id);
    }

    this.update = function update(_idlist, _this) {
        if (_this === "undefined") _this = this;

        // Scale the range of the data
        _this.cfg.idlist.forEach(function (d,i) {
            if ( d.visible == true )
            {
                if ( d.min_max_dates[0].getTime() < _this.min_max_dates[0].getTime() )
                {
                    _this.min_max_dates[0] = d.min_max_dates[0];
                }

                if ( d.min_max_dates[1].getTime() > _this.min_max_dates[1].getTime() )
                {
                    _this.min_max_dates[1] = d.min_max_dates[1];
                }

                if ( d.max_val > _this.max_val)
                {
                    _this.max_val = d.max_val;
                }
            }
        });

        _this.Logger.debug("%s: DATES = %s", arguments.callee.name, _this.min_max_dates);
        _this.x.domain(_this.min_max_dates);

        _this.y.domain([0,_this.max_val]);

        var svg = d3.select("#" + _this.placeholder).transition();

        svg.selectAll(".line").remove();
        svg.selectAll(".legend").remove();
        svg.select(".x.axis").duration(750).call(_this.xAxis);
        svg.select(".y.axis").duration(750).call(_this.yAxis);

        _this.cfg.idlist.forEach(function(d,i) {
            if ( d.visible == true )
            {
                // Add the valueline path.
                d3.select("#_" + _this.placeholder).append("path")
                    .attr("class", "line")
                    .style("stroke", function() {
                        return d.color = _this.cfg.color(d.id); })
                    .attr("d", _this.valueline(d.data));
            }

            d3.select("#_" + _this.placeholder)
              .append("text")
                  .attr("x", (_this.width-_this.margin.right))
                  .attr("y", "-.5em")
                  .attr("dy", i.toString() +"em")
                  .attr("class", "legend")    // style the legend
                  .style("fill", function() { // dynamic colours
                      return d.color = _this.cfg.color(d.id); })
                  .text(_this.cfg[d.id].title);

            d3.select("#_" + _this.placeholder)
                .append("circle")
                    .attr("context", _this)
                    .attr("id", d.id + " " + _this.placeholder)
                    .attr("cx", (_this.width-_this.margin.right - 10))
                    .attr("cy", ((i-1).toString())+"em")
                    .attr("stroke", "black")
                    .attr("stroke-width","2")
                    //.attr("dy", i.toString() +"em")
                    .attr("r", 5)
                    .attr("class", "legendToggle")    // style the legend
                    .on("click", _this.toggleVisible)
                    .style("fill", function() { // dynamic colours
                        return (_this.cfg[d.id].visible == false) ? "white" : d.color = _this.cfg.color(d.id); });
        });
    };

    // Set the dimensions of the canvas / graph
    this.margin = {top: 30, right: 100, bottom: 70, left: 50};
    this.width = this.cfg.width - this.margin.left - this.margin.right;
    this.height = this.cfg.height - this.margin.top - this.margin.bottom;

    // Set the ranges
    this.x = d3.time.scale().range([0, this.width]);
    this.y = d3.scale.linear().range([this.height, 0]);

    // Define the axes
    this.xAxis = d3.svg.axis().scale(this.x)
        .orient("bottom").ticks(5);
    this.yAxis = d3.svg.axis().scale(this.y)
        .orient("left").ticks(5);

    // Define the line
    this.valueline = d3.svg.line()
        .interpolate("step-after")
        .x(function(d) { return this.x(d.date); })
        .y(function(d) { return this.y(d.val); });
    
    // Adds the svg canvas
    var svg = d3.select("#" + this.placeholder)
      .append("svg")
        .attr("width", this.width + this.margin.left + this.margin.right)
        .attr("height", this.height + this.margin.top + this.margin.bottom)
      .append("g")
        .attr("id", "_" + this.placeholder)
        .attr("transform", 
              "translate(" + this.margin.left + "," + this.margin.top + ")");

    // Add the X Axis
    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + this.height + ")")
        .call(this.xAxis)
       .append("text")
        .attr("y", (this.margin.bottom / 2))
        .attr("x", (this.width / 2))
        .attr("dy", "1.5em")
        .style("text-anchor", "middle")
        .text("Time - Starting at " + (d3.time.format("%c"))(this.min_max_dates[0]));

    // Add the Y Axis
    svg.append("g")
        .attr("class", "y axis")
        .call(this.yAxis)
       .append("text")
        .attr("transform", "rotate(-90)")
        .attr("y", 0 + (-1)*this.margin.left)
        .attr("x",0 - (this.height / 2))
        .attr("dy", ".5em")
        .style("text-anchor", "middle")
        .text("amps");

    // Add a title to the graph
    svg.append("text")
        .attr("x", (this.margin.left))				
        .attr("y", 0 - (this.margin.top / 2))
        .attr("text-anchor", "left")	
        .attr("id", "textTitle")
        .style("font-size", "16px") 
        .style("text-decoration", "underline") 	
        .text("Real Time Power Consumption");

    this.div = d3.select("#" + this.placeholder).append("div")	
        .attr("class", "tooltip")				
        .style("opacity", 0);
}