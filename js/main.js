$(document).ready(function() {
    console.log("Ready to work...");

    $("#search_bar_home .search_box").keyup(function() {
        var query = $("#search_bar_home .search_box").val();
        var host = window.location.hostname;
        var port = window.location.port;
        var url = "http://" + host + ":" + port + "/search.html?q=" + query;
        $("#query_display").html("Query: " + query);
        $.get(url, function(response) {
            var result = "";
            for (const entity of response) {
                result += `${entity["name"]}: ${entity["desc"]}<br>
                <img src="${entity["img"]}" alt="${entity["name"]} width="32" height="32"><br>
                <a href="${entity["url"]}">link</a><br><br>`
            }
            $("#results_display").html(result);

            console.log(response);
        })
    })
})
