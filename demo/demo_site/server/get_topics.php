<?php header('Access-Control-Allow-Origin: *'); ?>
<?php
$f = fopen("topics.csv", "r");
$topics = [];
$i = 1;
if ($f) 
{
    while (($data = fgetcsv($f, 1000, ",")) !== FALSE) 
    {
        if ((int)$data[0] === $i){

            $cur_topic = array(
                'topic_id' => $i,
                'topic_name' => $data[1],
            );
            array_push($topics, $cur_topic);
            $i ++;
        }
    }
}
echo json_encode($topics);
?>
