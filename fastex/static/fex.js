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
}

class ClassEntry {
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

  attach(fn) {
    if ($("#" + this.name).length > 0) {
      console.log("Already attached " + this.name + "doing nothing.");
      return;
    }
    const self = this;

    let obj = addInputGroup(
      undefined,
      // $("<label for='"+this.name+"'>"+this.name+"</label>"),
      $("<input type='text' id='"+this.name+"' class='form-control' placeholder='type " + this.name + "(s) here' tabindex='1'/>")
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
    return this.elem().val();
  }
}

//$('iframe').on('load', evt => resize(evt.target));
// $("#sidebar-submit").on("submit", evt => {
//   console.log(evt);
// });

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
    this.listeners.forEach(listener => listener(evt.target.value));
  }
  
  elem() {
    return $("#progress");
  }
  
  value(val) {
    this.elem().val(val)
  }
}

class LabelInterface {
  constructor() {
    this.progress = new ProgressBar();
    this.entry = new ClassEntry("intent");
    this.submit = new Button("Next", true);

    // Hook up progress bar to change document.
    this.progress.listeners.push(idx => {
      $('span#progress-idx').text(idx);
      $('iframe').attr("src", "/_/" + (idx-1));
    });

    // Hook up next button to submit data on completion and then update
    // the scroll bar.
    this.submit.listeners.push(submit => {
      if (!submit) return;

      let blob = {};
      blob.idx = self.idx;
      blob["intent"] = self.entry.value();

      $.ajax({
        url: "/update/",
        dataType: "json",
        data: blob,
        success: function(data) {
          self.setIdx(self.progress.value() + 1);
        }
      });
    });
  }

  setIdx(idx) {
  }

  attach(fn) {
    if ($("#interface").length > 0) {
      console.log("#interface already attached");
      return;
    }
    let node = $("<div id='interface'></div>");
    this.progress.attach(widget => node.append(widget));
    this.entry.attach(widget => node.append(widget));
    this.submit.attach(widget => node.append(widget));

    fn(node);
  }
}

function fex_init(root) {
  let interface = new LabelInterface();
  interface.attach(node => root.append(node));
}
