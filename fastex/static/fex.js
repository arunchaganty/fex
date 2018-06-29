// Utility functions
function resize(obj) {
  obj.style.height = obj.contentWindow.document.body.scrollHeight + 'px';
}

function split( val ) {
  return val.split( /,\s*/ );
}

function extractLast( term ) {
  return split( term ).pop();
}

function addInputGroup(label, input) {
  let ret = $("<div class='input-group mb-2'></div>");
  if (label !== undefined) ret.append(label);
  ret.append(input);
  return ret;
}

// Widgets
class Button {
  constructor(name, isSubmit) {
    this.name = name;
    this.isSubmit = isSubmit || false;
    this.handleClick = this.handleClick.bind(this);
    this.listeners = [];
  }

  handleClick(evt) {
    console.log(evt);
    this.listeners.forEach(listener => listener(true));
  }

  attach(fn) {
    fn(addInputGroup(undefined,
      $('<input id="'+this.name+'" type="submit" class="btn btn-primary" value="'+this.name+'" />')
      .on("click", this.handleClick)
    ));
  }

  elem() {
    return $("#" + this.name);
  }
}

class TextWidget {
  constructor(name) {
    this.name = name;
    this.listeners = [];

    this.handleChange = this.handleChange.bind(this);
  }

  handleChange(evt) {
    let val = this.value();
    this.listeners.forEach(listener => listener(val));
  }

  attach(fn) {
    if ($("#" + this.name).length > 0) {
      console.log("Already attached " + this.name + "doing nothing.");
      return;
    }
    const self = this;

    let obj = addInputGroup(
      undefined,
      // $("<label for='"+this.name+"'>"+this.name+"</label>"),
      $("<textarea id='"+this.name+"' class='form-control' placeholder='type " + this.name + "(s) here'></textarea>")
        .on("change", this.handleChange)
    );
    fn(obj);
  }

  elem() {
    return $("#" + this.name);
  }

  value() {
    let terms = split(this.elem().val());
    return terms;
  }

  setValue(val) {
    this.elem().val(val);
  }

  clear() {
    this.setValue("");
  }

  dirty() {}
}


class MultiLabelWidget {
  constructor(name) {
    this.name = name;
    this._choices = [];
    this._dirty = true;
    this.listeners = [];

    this.handleChange = this.handleChange.bind(this);
  }

  handleChange(evt) {
    let val = this.value();
    this.listeners.forEach(listener => listener(val));
  }

  dirty() {
    this._dirty = true;
  }

  attach(fn) {
    if ($("#" + this.name).length > 0) {
      console.log("Already attached " + this.name + "doing nothing.");
      return;
    }
    const self = this;

    let obj = addInputGroup(
      undefined,
      // $("<label for='"+this.name+"'>"+this.name+"</label>"),
      $("<input type='text' id='"+this.name+"' class='form-control' placeholder='type " + this.name + "(s) here' />")
        // don't navigate away from the field on tab when selecting an item
        .on( "keydown", function( event ) {
          if ( event.keyCode === $.ui.keyCode.TAB &&
              $( this ).autocomplete( "instance" ).menu.active ) {
            event.preventDefault();
          }
        })
        .on("change", this.handleChange)
        .autocomplete({
          minLength: 0,
          source: function( request, response ) {
            const term = extractLast(request.term);
            self.choices(choices => response($.ui.autocomplete.filter(choices, term)));
          },
          focus: function() {
            // prevent value inserted on focus
            return false;
          },
          select: function( event, ui ) {
            var terms = split( this.value );
            // remove the current input
            terms.pop();
            // add the selected item
            terms.push( ui.item.value );
            // add placeholder to get the comma-and-space at the end
            terms.push( "" );
            this.value = terms.join( ", " );
            return false;
          }
        })
    );
    fn(obj);
  }

  choices(fn) {
    let self = this; 
    if (this._dirty) {
      // delegate back to autocomplete, but extract the last term
      $.ajax({
        url: "/autocomplete/",
        dataType: "json",
        data: {
          name: self.name,
        },
        success: function(data) {
          self._choices = data;
          self._dirty = false;
          console.log(self._choices);
          fn(self._choices);
        }
      });
    } else {
      console.log(self._choices);
      fn(self._choices);
    }
  }

  elem() {
    return $("#" + this.name);
  }

  value() {
    let terms = split(this.elem().val());
    return terms;
  }

  setValue(vs) {
    console.log(vs);
    this.elem().val(vs.join( ", " ));
  }

  clear() {
    this.setValue([]);
  }
}

class ProgressBar {
  constructor() {
    this._dirty = true;
    this._limit = 1;

    this.handleChange = this.handleChange.bind(this);
    this.listeners = [];
  }

  limit(fn) {
    let self = this;

    if (this._dirty) {
      $.ajax({
        url: "/count/",
        dataType: "json",
        data: {},
        success: function(data) {
          self._limit = data;
          self._dirty = false;
          fn(self._limit);
        }
      });
    } else {
      fn(self._limit);
    }
  }

  attach(fn) {
    if ($("#progress").length > 0) {
      console.log("#progress already attached");
      return;
    }

    fn(addInputGroup(
      $("<label for='range'>Element #<span id='progress-idx'>1</span></label>"),
      $("<input type='range' class='custom-range' id='progress' min='1' max='1' value='1' />")
        .on("input", this.handlePreviewChange)
        .on("change", this.handleChange)
    ))

    // Get the limit async
    this.limit(val => $("#progress").attr("max", val));
  }
  handlePreviewChange(evt) {
    const idx = evt.target.value;
    $('span#progress-idx').innerText = idx;
  }
  handleChange(evt) {
    this.listeners.forEach(listener => listener(Number.parseInt(evt.target.value)));
  }
  
  elem() {
    return $("#progress");
  }

  value() {
    return  Number.parseInt(this.elem().val());
  }

  setValue(val) {
    this.elem().val(val);
  }

  clear() {
    this.setValue(1);
  }
}

class LabelInterface {
  constructor(schema) {
    this.progress = new ProgressBar();
    this.submit = new Button("Next", true);

    this.widgets = [];
    for (let key of Object.keys(schema)) {
      if (schema[key].type === "multilabel") {
        this.widgets.push(new MultiLabelWidget(key));
      } else if (schema[key].type === "text") {
        this.widgets.push(new TextWidget(key));
      } else {
        console.error("Could not add widget for type " + schema[key].type);
      }
    }

    let self = this;
    // Hook up progress bar to change document.
    this.progress.listeners.push(idx => {
      self.setIdx(idx);
    });

    // Hook up next button to submit data on completion and then update
    // the scroll bar.
    this.submit.listeners.push(submit => {
      if (!submit) return;

      let blob = {};
      blob["_idx"] = self.progress.value() - 1;
      for (let widget of self.widgets) {
        blob[widget.name] = widget.value();
      }
      console.log(blob);

      $.ajax({
        url: "/update/",
        contentType: "application/json",
        method: "post",
        data: JSON.stringify(blob),
        dataType: "json",
        success: function(data) {
          self.widgets.forEach(w => w.dirty());
          self.setIdx(self.progress.value() + 1);
        }
      });
    });
  }

  setIdx(idx) {
    let self = this;

    this.progress.limit(lim => {
      if (idx <= lim) {
        $('input#progress').val(idx);
        $('span#progress-idx').text(idx);
        $('iframe').attr("src", "/_/" + (idx-1));

        $.ajax({
          url: "/get/" + (idx-1),
          method: "get",
          dataType: "json",
          success: data => {
            for (let widget of self.widgets) {
              if (data[widget.name]) {
                widget.setValue(data[widget.name]);
              } else {
                widget.clear();
              }
            }
          },
        });
      } else {
        console.warn("Tried to cross last possible index.");
      }
    });
  }

  attach(fn) {
    if ($("#interface").length > 0) {
      console.log("#interface already attached");
      return;
    }
    let node = $("<div id='interface'></div>");
    this.progress.attach(widget => node.append(widget));
    for (let widget of this.widgets) {
      widget.attach(widget => node.append(widget));
    }
    this.submit.attach(widget => node.append(widget));

    fn(node);
  }
}

function fex_init(root, schema) {
  let interface = new LabelInterface(schema);
  interface.attach(node => root.append(node));
  interface.setIdx(1);

  $('iframe').on('load', evt => resize(evt.target));
}
