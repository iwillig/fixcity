function expandOnce(selector, text) {
  var target=$(selector);
  $('<span class="expandonce">' + text +'</span>').prependTo(target).click(function() {$(this).siblings().removeClass("noshow").end().remove();}).siblings().addClass("noshow");
}