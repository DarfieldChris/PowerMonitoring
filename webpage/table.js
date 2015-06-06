function Table(placeholder, cfg)
{
    this.Logger = Logger.get('table');
    this.placeholder = placeholder;
    this.cfg = cfg;
    this.id = "";

    this.update = function update(_idlist, _this) {
        if (_this === "undefined") _this = this;

        _this.sel
         .selectAll("option")
         .data(_this.cfg.idlist)
         .enter()
         .append("option")
             .attr("class", "select-inline")
             .attr("value", function(d){return d.id;})
             .html(function(d){return d.title;});

        _this.id = $("#" + _this.placeholder + "_select").val();
        _this.Logger.debug(arguments.callee.name +  ": Selected table is " + _this.id);

        if (_this.id !== "undefined" ) {
            var columns = ["date", "val"];

            // append the header row
            _this.thead_tr
                .selectAll("th")
                .data(columns)
                .enter()
                .append("th")
                    .text(function(column) { return column; });

            // create a row for each object in the data
            var rows = _this.tbody.selectAll("tr")
                .data(_this.cfg[_this.id].data, function(d) { return d.id+d.date; });
            rows.enter().append("tr");
            rows.exit().remove();

            // create a cell in each row for each column
            var cells = rows.selectAll("td")
                .data(function(row) {
                    return columns.map(function(column) {
                        return {column: column, value: row[column]};
                    });
                })
                .enter()
                .append("td")
                .attr("style", "font-family: Courier")
                .html(function(d) { return d.value; });
        }

        return _this.table;
    };

    // render radio buttons
    this.form = d3.select("#" + this.placeholder).append("form");
    this.sel  = this.form.append("select")
                     .attr("id", this.placeholder + "_select")
                     .attr("name", "select_table")
                     .on("change", function (d) {
                         var _target = d3.event.target.id;
                         var _target = _target.split("_");
                         var _placeholder = _target[0];

                         // HACK - NOT SURE HOW TO DO THIS FROM EVENT? - CSN
                         _this = window.wpd3.tabs[_placeholder];

                         _this.Logger.debug("On Change ..." + _placeholder);
                         (_this.update)([], _this);
                     });

    this.sel.append("optgroup")
             .attr("label", "Select a circuit ...");

    // render the table
    this.table = d3.select("#" + this.placeholder).append("table");
    this.thead =  this.table.append("thead");
    this.thead_tr = this.thead.append("tr");
    this.tbody = this.table.append("tbody");
}