function expandOnce(selector, text) {
  var target=$(selector);
  $('<span class="expandonce">' + text +'</span>').prependTo(target).click(function() {$(this).siblings().show().end().remove();}).siblings().hide();
}