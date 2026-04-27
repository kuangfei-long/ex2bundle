<?php header('Access-Control-Allow-Origin: *'); ?>
<?php
$f = fopen("data.csv", "r");
$states = [];
$i = 1;
if ($f) 
{
    while (($data = fgetcsv($f, 1000, ",")) !== FALSE) 
    {
        if ((int)$data[1] === $i){

            $cur_state = array(
                'state_id' => $i,
                'state_name' => $data[2],
            );
            array_push($states, $cur_state);
            $i ++;
        }
    }
}
echo json_encode($states);
?>