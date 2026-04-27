<?php header('Access-Control-Allow-Origin: *'); ?>
<?php
$state = $_POST['state'];
$bounds = $_POST['bounds'];

$last_id = -100;
$ids = fopen("Requests/ids.txt", "r");
$new_id = intval(fgets($ids)) + 1;
fclose($ids);

$ids = fopen("Requests/ids.txt", "w");
fwrite($ids, strval($new_id));
fclose($ids);

$new_request = fopen("Requests/request_".strval($new_id).".txt", "w");
fwrite($new_request, $state."\n".$bounds);
fclose($new_request);
chmod($new_request, 0777);

$response_file = "Requests/response_".strval($new_id).".txt";
$attempt = 0;
while($attempt < 60){
    if(file_exists($response_file) ){
        $summary = file($response_file);
        array_pop($summary); 
        $summary = join('', $summary); 
        echo ($summary);
        unlink($response_file);
        break;
    }
    sleep(1);
    $attempt ++;
}

if ($attempt == 60){
    echo ("Timed out!");
}
?>