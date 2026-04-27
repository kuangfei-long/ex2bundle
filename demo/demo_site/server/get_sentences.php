<?php header('Access-Control-Allow-Origin: *'); ?>
<?php
$f = fopen("data.csv", "r");
$state_id = $_GET['state_id'];
$sentences = [];
while (($data = fgetcsv($f, 1000, ",")) !== FALSE) 
{
    if ($data[1] === $state_id) {

        $cur_sent = array(
            'sentence_id' => (int)$data[3],
            'text' => $data[4],
        );
        array_push($sentences, $cur_sent);
    }
}
echo json_encode($sentences);
?>