<?php header('Access-Control-Allow-Origin: *'); ?>
<?php

$bounds = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
$stateName = $_POST['state_name'];
$bounds = $_POST['bounds'];
$bounds = explode(" ", $bounds);

$lb = array($bounds[0], $bounds[2], $bounds[4], $bounds[6], $bounds[8], $bounds[10], $bounds[12], $bounds[14], $bounds[16], $bounds[18]);
$ub = array($bounds[1], $bounds[3], $bounds[5], $bounds[7], $bounds[9], $bounds[11], $bounds[13], $bounds[15], $bounds[17], $bounds[19]);

$paql =
    '{"first_segment":"SELECT PACKAGE(*)<br/>FROM state_sentences<br/>WHERE state = \''.$stateName.'\'<br/>SUCH THAT<br/>",
    "topics": 
        [ 
            {"topic_id":1,  "lb": '.$lb[0].', "ub": '.$ub[0].', "details": "national, near, major, popular, system, founded, home, construction, highways, world"},  
            {"topic_id":2,  "lb": '.$lb[1].', "ub": '.$ub[1].', "details": "governor, election, elected, vote, democratic, elections, counties, majority, presidential, language"},  
            {"topic_id":3,  "lb": '.$lb[2].', "ub": '.$ub[2].', "details": "century, passed, legislature, constitution, created, law, political, white, late, laws"},  
            {"topic_id":4,  "lb": '.$lb[3].', "ub": '.$ub[3].', "details": "population, largest, city, cities, percent, metropolitan, total, miles, capital, people"},  
            {"topic_id":5,  "lb": '.$lb[4].', "ub": '.$ub[4].', "details": "major, economy, largest, industry, home, billion, teams, production, team, oil"},  
            {"topic_id":6,  "lb": '.$lb[5].', "ub": '.$ub[5].', "details": "american, people, native, french, century, day, settlers, european, spanish, tribes"},  
            {"topic_id":7,  "lb": '.$lb[6].', "ub": '.$ub[6].', "details": "climate, feet, temperature, rail, service, temperatures, recorded, forests, summer, winter"},  
            {"topic_id":8,  "lb": '.$lb[7].', "ub": '.$ub[7].', "details": "north, west, south, east, southern, eastern, region, western, central, northern"},  
            {"topic_id":9,  "lb": '.$lb[8].', "ub": '.$ub[8].', "details": "tax, income, rate, ranked, nation, sales, average, taxes, capita, universities"},  
            {"topic_id":10, "lb": '.$lb[9].', "ub": '.$ub[9].', "details": "government, school, county, public, federal, schools, law, power, court, system"}
        ],
        
        "last_segment": "MAXIMIZE SUM(score);"
    }';
echo $paql;
?>
