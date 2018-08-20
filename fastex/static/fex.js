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

function makeid(length) {
  var text = "";
  var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

  for (var i = 0; i < length; i++)
    text += possible.charAt(Math.floor(Math.random() * possible.length));

  return text;
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
    this.id = name + '_' + makeid(5);
    this.listeners = [];

    this.handleChange = this.handleChange.bind(this);
  }

  handleChange(evt) {
    let val = this.value();
    this.listeners.forEach(listener => listener(val));
  }

  attach(fn) {
    if ($("#" + this.id).length > 0) {
      console.log("Already attached " + this.id + "doing nothing.");
      return;
    }
    const self = this;

    let obj = addInputGroup(
      undefined,
      // $("<label for='"+this.name+"'>"+this.name+"</label>"),
      $("<textarea id='"+this.id+"' class='form-control' placeholder='type " + this.name + "(s) here'></textarea>")
        .on("change", this.handleChange)
    );
    fn(obj);
  }

  elem() {
    return $("#" + this.id);
  }

  value() {
    let terms = split(this.elem().val());
    return terms;
  }

  setValue(val) {
    this.elem().val(val);
  }

  setFocus() {
    // console.log('set focus', this.name);
    //this.elem().focus();
    this.elem().click();
  }

  clear() {
    this.setValue("");
  }

  dirty() {}
}


class MultiLabelWidget {
  constructor(name) {
    this.name = name;
    this.id = name + '_' + makeid(5);
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
    if ($("#" + this.id).length > 0) {
      console.log("Already attached " + this.name + "doing nothing.");
      return;
    }
    const self = this;

    let obj = addInputGroup(
      undefined,
      // $("<label for='"+this.name+"'>"+this.name+"</label>"),
      $("<input type='text' id='"+this.id+"' class='form-control' placeholder='type " + this.name + "(s) here' />")
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
    return $("#" + this.id);
  }

  value() {
    let terms = split(this.elem().val());
    return terms;
  }

  setValue(vs) {
    this.elem().val(vs.join( ", " ));
  }

  setFocus() {
    //console.log('set focus', this.name, this.id);
    //this.elem().get(0).focus();
    this.elem().click();
  }

  clear() {
    this.setValue([]);
  }
}

class ComboLabelWidget {
  constructor(name, schema) {
    console.log('processing', schema);
    this.name = name;

    this.widgets = [];
    for (let key of Object.keys(schema)) {
      let baseWidget = null;
      let key_info = schema[key];
      let typename = (typeof key_info.type === "string")? key_info.type  : key_info.type.type;
      if (typename === "multilabel") {
        baseWidget = new MultiLabelWidget(key);
      } else if (typename === "text") {
        baseWidget = new TextWidget(key);
      } else if (typename === "record") {
        let fields = (typeof key_info.type === "string")? key_info.fields : key_info.type.fields;
        baseWidget = new ComboLabelWidget(key, fields);
      } else {
        console.error("Could not add widget for type " + typename);
      }
      if (baseWidget) {
        if (schema[key].repeated) {
          this.widgets.push(new RepeatedLabelWidget(baseWidget, schema[key].useMap));
        } else {
          this.widgets.push(baseWidget);
        }
      }
    }
  }

  getWidget(fieldname) {
    let path = Array.isArray(fieldname)? fieldname : fieldname.split('.');
    var matched = null;
    for (let widget of this.widgets) {
      if (widget.name === path[0]) {
        matched = widget;
        break;
      }
    }
    if (matched && path.length > 1) {
      if (matched.getWidget) {
        return matched.getWidget(path.slice(1));
      } else {
        return null;
      }
    } else {
      return matched;
    }
  }

  value() {
    let blob = {};
    for (let widget of this.widgets) {
      blob[widget.name] = widget.value();
    }
    return blob;
  }

  setValue(data) {
    if (data) {
      for (let widget of this.widgets) {
        if (data[widget.name]) {
          widget.setValue(data[widget.name]);
        } else {
          widget.clear();
        }
      }
    } else {
      this.clear();
    }
  }

  setFocus() {
    this.widgets[0].setFocus();
  }

  clear() {
    for (let widget of this.widgets) {
      widget.clear();
    }
  }

  dirty() {
    this.widgets.forEach(w => w.dirty());
  }

  attach(fn) {
    if ($("#" + this.name).length > 0) {
      console.log("#" + this.name + " already attached");
      return;
    }
    let node = $("<div id='" + this.name + "'></div>");
    for (let widget of this.widgets) {
      widget.attach(widget => node.append(widget));
    }

    fn(node);
  }
}

class RepeatedLabelWidget {
  constructor(widget, useMap) {
    this.name = widget.name;
    this.widget = widget;
    this.useMap = useMap;
    this.data = useMap? {} : [];
    this.key = null;
  }

  setKey(key) {
    this.key = key;
    if (key != undefined) {
      this.__label.text(this.name + ': ' + key);
    } else {
      this.__label.text(this.name);
    }
    this.widget.setValue(this.data[this.key]);
  }

  setFocus() {
    this.widget.setFocus();
  }

  value() {
    return this.data;
  }

  setValue(data) {
    this.data = data;
    if (this.key != null) {
      this.widget.setValue(this.data[this.key]);
    }
  }

  save() {
    if (this.key != null) {
      this.data[this.key] = this.widget.value();
    }
  }

  clearEntry() {
    this.widget.clear();
    this.save();
  }

  clear() {
    this.data = this.useMap? {} : [];
    this.widget.clear();
    this.key = null;
  }

  dirty() {
    this.clear();
    this.widget.dirty();
  }

  attach(fn) {
    let self = this;
    this.__label = $('<div></div>').text(this.name);
    this.widget.attach(node => {
      node.prepend(self.__label);
      node.focusout(function() { self.save(); });
      fn(node);
    });
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

    this.widget = new ComboLabelWidget("interface", schema);

    let self = this;
    // Hook up progress bar to change document.
    this.progress.listeners.push(idx => {
      self.setIdx(idx);
    });

    // Hook up next button to submit data on completion and then update
    // the scroll bar.
    this.submit.listeners.push(submit => {
      if (!submit) return;

      let blob = self.widget.value();
      blob["_idx"] = self.progress.value() - 1;
      console.log(blob);

      $.ajax({
        url: "/update/",
        contentType: "application/json",
        method: "post",
        data: JSON.stringify(blob),
        dataType: "json",
        success: function(data) {
          self.widget.dirty();
          self.setIdx(self.progress.value() + 1);
        }
      });
    });
  }

  getIdx(idx) {
    return this.progress.value();
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
            self.widget.setValue(data);
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
    let self = this;
    this.widget.attach(node => {
      self.progress.attach(widget => node.prepend(widget));
      self.submit.attach(widget => node.append(widget));
      fn(node);
    });
  }
}

class SearchWidget {
  constructor(labelInterface) {
     this.filtered_indices = null;
     this.search_text = null;
     this.labelInterface = labelInterface;
  }

  gotoPrev() {
    let self = this;
    const idx = self.labelInterface.getIdx();
    if (self.filtered_indices && self.filtered_indices.length) {
      const fidx = self.filtered_indices.findIndex(function(x) { return x >= (idx-1); });
      // console.log('got index ' + fidx, idx);
      if (fidx > 0) {
        self.labelInterface.setIdx(self.filtered_indices[fidx-1]+1);
      } else {
        self.labelInterface.setIdx(self.filtered_indices[self.filtered_indices.length-1]+1);
      }
    } else {
      self.labelInterface.setIdx(idx-1);
    }
  }

  gotoNext() {
    let self = this;
    const idx = self.labelInterface.getIdx();
    if (self.filtered_indices && self.filtered_indices.length) {
      const fidx = self.filtered_indices.findIndex(function(x) { return x > (idx-1); });
      // console.log('got index ' + fidx, idx);
      if (fidx >= 0) {
        self.labelInterface.setIdx(self.filtered_indices[fidx]+1);
      } else {
        self.labelInterface.setIdx(self.filtered_indices[0]+1);
      }
    } else {
      self.labelInterface.setIdx(idx+1);
    }
  }

  search(search_text) {
    let self = this;
    if (search_text != undefined) {
      self.__searchTextbox.val(search_text);
    } else {
      search_text = self.__searchTextbox.val();
    }
    if (search_text.length > 0) {
        console.log('searching for ', search_text);
        $.ajax({
          url: "/search/",
          contentType: "application/json",
          method: "post",
          data: JSON.stringify({ query: search_text }),
          dataType: "json",
          success: function(data) {
            console.log('got', data);
            self.filtered_indices = data;
            // console.log(filtered_indices);
            self.search_text = search_text;
            if (self.filtered_indices && self.filtered_indices.length) {
              self.labelInterface.setIdx(self.filtered_indices[0]+1);
              // TODO: don't peak!s
              var total = self.labelInterface.progress.elem().attr('max');
              self.__messageElement.text('Matched ' + self.filtered_indices.length + '/' + total);
            } else {
              self.__messageElement.text('No matches');
            }
          }
        });
    } else {
      this.clear();
      self.search_text = search_text;
    }
  }

  clear() {
    this.filtered_indices= null;
    self.__messageElement.text('');
  }

  attach(fn) {
    if ($("#searchForm").length > 0) {
      console.log("#searchForm already attached");
      return;
    }

    let self = this;
    let div = $('<div></div>');
    let form = $('<div class="form-inline" id="searchForm"/>');
    let inputGroup = $('<div class="input-group mb-2 mr-sm-2" />');
    form.append(inputGroup);

    let filterButton = $('<span class="input-group-text"/>').text('Filter')
      .click(event => self.search());
    inputGroup.append(
      $('<div class="input-group-prepend" style="cursor: default;"/>').append(filterButton)
    );
    let searchTextbox = $('<input type="text" id="search" class="form-control" />')
      .change(event => self.search());
    inputGroup.append(searchTextbox);
    self.__searchTextbox = searchTextbox;

    let leftButton = $('<span class="oi oi-chevron-left" title="chevron left" aria-hidden="true" />')
      .click(event => self.gotoPrev());
    let rightButton = $('<span class="oi oi-chevron-right" title="chevron right" aria-hidden="true" />')
      .click(event => self.gotoNext());
    inputGroup.append(
      $('<div class="input-group-append" />')
        .append($('<span class="input-group-text"/>').append(leftButton))
        .append($('<span class="input-group-text"/>').append(rightButton)));
    let messageElement = $('<div id="matched" />');
    self.__messageElement = messageElement;

    div.append(form);
    div.append(messageElement);

    window.addEventListener("keyup", function(event) {
      var tagName = (event.target || event.srcElement).tagName;
      if (tagName === 'INPUT' || tagName === 'SELECT' || tagName === 'TEXTAREA') {
        return;
      }
      if (event.keyCode === 78 /* 'n' */ ) {
        self.gotoNext();
      } else if (event.keyCode === 80 /* 'p' */ ) {
        self.gotoPrev();
      }
    });

    fn(div);
  }
}

function attach_key_listeners(options) {
  window.addEventListener("keyup", function (event) {
    var tagName = (event.target || event.srcElement).tagName;
    if (tagName === 'INPUT' || tagName === 'SELECT' || tagName === 'TEXTAREA') {
      if (event.keyCode === 13) {
        var focusable = $('input,select,textarea').filter(':visible');
        // console.log(focusable, this, focusable.index($(event.target)));
        var next = focusable.eq(focusable.index($(event.target)) + 1);
        if (next.length) {
          next.focus();
        }
        return false;
      }
    }
  });
}

function attach_child_message_handler(interface, searchWidget) {
  window.addEventListener('message', function(event) {
    var message = JSON.parse(event.data);
    if (message.action === 'gotoItem') {
      interface.setIdx(message.idx);
    } else if (message.action === 'gotoPrevFilteredItem' && searchWidget) {
      searchWidget.gotoPrev();
    } else if (message.action === 'gotoNextFilteredItem' && searchWidget) {
      searchWidget.gotoNext();
    } else if (message.action === 'saveAnnotation') {
      if (message.field) {
        let widget = interface.widget.getWidget(message.field);
        if (widget) {
          if (widget.save) {
            widget.save();
          }
        } else {
          console.warn('Field ' + message.field + ' not found');
        }
      } else {
        //interface.widget.save();
      }
    } else if (message.action === 'setAnnotationFieldId') {
      let widget = interface.widget.getWidget(message.field);
      if (widget) {
        widget.setKey(message.id);
        widget.setFocus();
      } else {
        console.warn('Field ' + message.field + ' not found');
      }
    } else if (message.action === 'makeCard') {
      let element = $(message.element);
      if (!element.hasClass('card')) {
        element.addClass('card');
      }
      let children = element.children();
      if (children.length > 1) {
        let div = $('<div class="card-body"></div>');
        for (child of children) {
          div.append(child);
        }
        element.append(div);
      }
    } else if (message.action === 'positionElement') {
      let element = $(message.element);
      $('body').append(element);
      element.css("position", "absolute");
      element.css("top", message.position.y);
      element.css("left", message.position.x);
    } else {
      console.error('Unsupported message', message);
    }
  },false);

}

function fex_init(root, schema, options) {
  let interface = new LabelInterface(schema);
  let searchWidget = null;
  interface.attach(node => root.append(node));
  interface.setIdx(1);
  if (options && options.search) {
    searchWidget = new SearchWidget(interface);
    searchWidget.attach(node => options.search.parent.append(node));
  }
  attach_key_listeners();
  attach_child_message_handler(interface, searchWidget);

  $('iframe').on('load', evt => resize(evt.target));
}
