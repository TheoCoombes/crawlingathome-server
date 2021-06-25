function timeDifference(current, previous) {

    var sPerMinute = 60;
    var sPerHour = sPerMinute * 60;
    var sPerDay = sPerHour * 24;
    var sPerMonth = sPerDay * 30;
    var sPerYear = sPerDay * 365;

    var elapsed = current - previous;

    if (elapsed < sPerMinute) {
        var ago = Math.round(elapsed);
        if (ago == 1) {
            return ago + ' second ago';
        } else {
            return ago + ' seconds ago';  
        }
    }

    else if (elapsed < sPerHour) {
        var ago = Math.round(elapsed/sPerMinute);
        if (ago == 1) {
            return ago + ' minute ago';
        } else {
            return ago + ' minutes ago';  
        }   
    }

    else if (elapsed < sPerDay ) {
        var ago = Math.round(elapsed/sPerHour);
        if (ago == 1) {
            return ago + ' hour ago';
        } else {
            return ago + ' hours ago';  
        }  
    }

    else if (elapsed < sPerMonth) {
        var ago = Math.round(elapsed/sPerDay);
        if (ago == 1) {
            return ago + ' day ago';
        } else {
            return ago + ' days ago';  
        }   
    }

    else if (elapsed < sPerYear) {
        var ago = Math.round(elapsed/sPerMonth);
        if (ago == 1) {
            return ago + ' month ago';
        } else {
            return ago + ' month ago';  
        }    
    }

    else {
        var ago = Math.round(elapsed/sPerYear);
        if (ago == 1) {
            return ago + ' year ago';
        } else {
            return ago + ' years ago';  
        }    
    }
}

$(document).ready(function() {
    var current = Math.floor(Date.now() / 1000);

    $('.timestamp').each(function() {
        var prev = parseInt($(this).text());
        var diff = timeDifference(current, prev);
        $(this).text(diff);
    })
})
