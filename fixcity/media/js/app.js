function expandOnce(selector, text) {
  var target=$(selector);
  $('<span class="expandonce">' + text +'</span>').prependTo(target).click(function() {$(this).siblings().removeClass("noshow").end().remove();}).siblings().addClass("noshow");
}

jQuery.fn.infoSuffixify = function() { //chainable
	return this.each(function() {
		var obj = $(this);
		$('<img src="/site_media/img/info.png" alt="More information about this field" title="' + obj.attr('title') + '" />').appendTo('label[for="' + obj.attr('id') + '"]');
	});
}

// Taken from http://www.andrewpeace.com/textarea-maxlength.html
jQuery.fn.truncate = function(len)
{
  this.val(this.val().substring(0,len));
  return false;
}

jQuery.fn.maxLength = function(len)
{
  var maxLengthKeyPress = new Array();
  var maxLengthChange = new Array();
  var appleKeyOn = false;
  
  //the second argument should be true if len should be based on
  //the maxlength attribute instead of the input
  var useAttr = arguments.length>1 ? arguments[1] : false;
  
  var handleKeyUp = function(e)
  {
    //if the apple key (macs) is being pressed, set the indicator
    if(e.keyCode==224||e.keyCode==91)
      appleKeyOn = false;
  }
  
  var handleKeyDown = function(e)
  {
    //if the apple key (macs) is being released, turn off the indicator
    if(e.keyCode==224||e.keyCode==91)
      appleKeyOn = true;
  }
  
  var handleKeyPress = function(e)
  {   
    //if this keyCode does not increase the length of the textarea value,
    //just let it go
    if(appleKeyOn || (e.charCode==0&&e.keyCode!=13) || e.ctrlKey)
      return;

    //get the textarea element
    var textarea = $(this);
    //if the length should be based on the maxlength attribute instead of the
    //input, use that
    len = useAttr ? parseInt(textarea.attr('maxlength')) : len;
    //get the value of the textarea
    var val = textarea.val();
    //get the length of the current text selection
    var selected = Math.abs(textarea.attr('selectionStart') - textarea.attr('selectionEnd'));
    selected = isNaN(selected) ? 0 : selected;
    //if this is the maximum length
    if(val.length==len && selected<1)
      return false;
    else if(val.length>len && selected<(val.length-len))
      return textarea.truncate(len);
  };
  
  var handleChange = function(e)
  {
    //get the textarea element
    var textarea = $(this);
    
    //if the length should be based on the maxlength attribute instead of the
    //input, use that
    len = useAttr ? parseInt(textarea.attr('maxlength')) : len;
    
    //truncate the textarea to its proper length
    textarea.truncate(len);
  };
  
  //get the current keyup and change functions
  var removeKeyPress = maxLengthKeyPress[this.selector];
  var removeChange = maxLengthChange[this.selector];

  //remove the keyup and change functions from any matched elements in case
  //a maxlength was previously set and a new one is being set
  this.die('keypress', removeKeyPress);
  this.die('change', removeChange);
  
  if(len==0 && !useAttr)
    return;
  
  //set the keyup and change functions for this element set and all future
  //elements matching this selector
  this.live('keypress', handleKeyPress);
  this.live('change', handleChange);
  this.live('keydown', handleKeyDown);
  this.live('keyup', handleKeyUp);
  
  //save the current keyup and change functions so that they can be
  //remove later
  maxLengthKeyPress[this.selector] = handleKeyPress;
  maxLengthChange[this.selector] = handleChange;
  
  //trigger a keypress event so that the limit will be enforced
  this.keypress();
};
