<?php header('Access-Control-Allow-Origin: *'); ?>
<?php
$example = "'".$_POST['example']."'";

$ids = fopen("Requests/ids.txt", "r");
$new_id = intval(fgets($ids)) + 1;
fclose($ids);

$new_example = fopen("Requests/example_".strval($new_id).".txt", "w");
fwrite($new_example, $example."\n");
fclose($new_example);
chmod($new_example, 0777);

$python = `export PYTHONWARNINGS="ignore"; source env/bin/activate ; python learn_summarization.py {$example}`;
echo $python;
?>
