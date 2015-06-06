function tabTemplate(placeholder, cfg)
{
    //var self = this;  // internal d3 functions

    this.placeholder = placeholder;
    this.cfg = cfg;

    this.Logger = Logger.get('tabTemplate');

    this.Logger.debug(arguments.callee.name + ": Starting ...");


    this.update = function update(_idlist, _this) {
        _this.Logger.debug(arguments.callee.name + ": Starting ... " + _idlist + " " + _this);

        if (_this === "undefined" ) _this = this;
 
    };

    this.Logger.debug(arguments.callee.name + ": Done");
}
