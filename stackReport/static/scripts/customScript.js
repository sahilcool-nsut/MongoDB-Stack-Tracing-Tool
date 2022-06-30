
// For "View More" text in function names in final output page
$(document).ready(function() {
    var max = 200;
    $(".readMoreTextHide").each(function() {
        var str = $(this).text();
        if ($.trim(str).length > max) {
            var subStr = str.substring(0, max);
            var hiddenStr = str.substring(max, $.trim(str).length);
            $(this).empty().html(subStr);
            $(this).append(' <a href="javascript:void(0);" class="link">Expand..</a>');
            $(this).append('<span class="addText">' + hiddenStr + '</span>');
        }
    });
    $(".link").click(function() {
        $(this).siblings(".addText").contents().unwrap();
        $(this).remove();
    });
});
