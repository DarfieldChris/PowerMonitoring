<?php
     function parseInterval(&$data, &$cmp, &$query, &$query_cmp, $inter)
     {
       for ($x = 0; $x < mysql_num_rows($query); $x++) {
            $tmp = mysql_fetch_assoc($query);
            $tmp_date = date_parse($tmp["DATE_TIME"]);

            if ( $query_cmp ) {
                $tmp_cmp = mysql_fetch_assoc($query_cmp);
            }

            if ($x == 0) {
 //echo "3\r\n";
                $index = 0;
                $tmp["DATE_TIME"] = date("Y-m-d 00:00:00",strtotime($tmp["DATE_TIME"]));
                $data[$index] = $tmp;
                $working_date = $tmp_date;
                if ($query_cmp) {
                   $tmp_cmp["CIRCUIT"] = $tmp_cmp["CIRCUIT"]." (".$_GET['compare_to'].")";
                   $tmp_cmp["DATE_TIME"] = $tmp["DATE_TIME"];
                   $cmp[$index] = $tmp_cmp;
                }
            } else {
                if ($working_date[$inter] == $tmp_date[$inter] && $data[$index]["CIRCUIT"] == $tmp["CIRCUIT"]) {
//echo "WOrking: ".join(",", $tmp_date)."\r\n";
                    $data[$index]["POWER_KWH"] = $data[$index]["POWER_KWH"] + $tmp["POWER_KWH"];
                    if ($query_cmp) {
                        $cmp[$index]["POWER_KWH"] = $cmp[$index]["POWER_KWH"] + $tmp_cmp["POWER_KWH"];
                    }
                } else {
//echo "1\r\n";
                    $index = $index + 1;
                    $tmp["DATE_TIME"] = date("Y-m-d 00:00:00",strtotime($tmp["DATE_TIME"]));
                    $data[$index] = $tmp;
                    $working_date = $tmp_date;
                    if ($query_cmp) {
                        $tmp_cmp["CIRCUIT"] = $tmp_cmp["CIRCUIT"]." (".$_GET['compare_to'].")";
                        $tmp_cmp["DATE_TIME"] = $tmp["DATE_TIME"];
                        $cmp[$index] = $tmp_cmp;
                    }
                 }
            }
        }        
     }


    // figure out a start date and end date
    if (!array_key_exists('date_start', $_GET) ) {
        $dateStart = "2015/03/01";
    } else {
        $dateStart = $_GET['date_start'];
    }
//echo "Starting date: ".$dateStart."\r\n";

    if ( !array_key_exists('date_end', $_GET) ) {
        $dateEnd = "2015/03/01";
    } else {
        $dateEnd = $_GET['date_end'];
    }
//echo "Ending date: ".$dateEnd."\r\n";

    // is there any data to compare to?
    if ( array_key_exists('compare_to', $_GET) ) {
        $dateCompare = $_GET['compare_to'];
        $timeStart = strtotime($dateStart);

        $timeCmpStart = strtotime($dateCompare,$timeStart);
        $dateCmpStart = date("Y/m/d", $timeCmpStart);

        $timeEnd = strtotime($dateEnd);
        $timeCmpEnd = strtotime($dateCompare, $timeEnd);
        $dateCmpEnd = date("Y/m/d", $timeCmpEnd);
//echo "Compare to start date: ".$dateCmpStart."\r\n";
//echo "Compare to end date: ".$dateCmpEnd."\r\n";
    }

    // what circuits/accounts do I want data on?
    $sql_circuits = "";
    if ( array_key_exists('circuits', $_GET) ) {
        $sql_circuits = " AND `CIRCUIT` IN (";
        $circuits = explode(",",$_GET['circuits']);
        $cnt = 0;
        foreach ($circuits as $circuit) {
            if ($cnt > 0 ) $sql_circuits=$sqlcircuits.",";
            $sql_circuits = $sql_circuits."'".$circuit."'";
            $cnt = $cnt +1;
        }
        $sql_circuits = $sql_circuits.") ";
    }
//echo "Circuits: ".$sql_circuits."\r\n";

    // time interval to use
    if ( !array_key_exists('interval', $_GET) ) {
        $interval = "hour";
    } else {
        $interval = $_GET['interval'];
    }
//echo "Interval: ".$interval."\r\n";

    // database administrative details
    $username = "darfield_python"; 
    $password = "1Python1!";   
    $host = "localhost";
    $database="darfield_development";
    
    $server = mysql_connect($host, $username, $password);
    $connection = mysql_select_db($database, $server);

    $myquery = "
SELECT `CIRCUIT`,`DATE_TIME`,`POWER_KWH` FROM `BCHYDRO_DATA` WHERE `DATE_TIME` BETWEEN '".$dateStart."' AND '".$dateEnd." 23:59'
".$sql_circuits." ORDER BY `CIRCUIT`,`DATE_TIME`";
//echo "SQL QUERY: ".$myquery."\r\n";
    $query = mysql_query($myquery);
    
    if ( ! $query ) {
        echo mysql_error();
        die;
    }
    
    if ( array_key_exists('compare_to', $_GET) ) {
        $myquery_cmp = "
SELECT `CIRCUIT`,`DATE_TIME`,`POWER_KWH` FROM `BCHYDRO_DATA` WHERE `DATE_TIME` BETWEEN '".$dateCmpStart."' AND '".$dateCmpEnd." 23:59'
".$sql_circuits." ORDER BY `CIRCUIT`,`DATE_TIME`";
//echo $myquery_cmp;
        $query_cmp = mysql_query($myquery_cmp);
        if ( ! $query_cmp ) {
            echo mysql_error();
            die;
        }
    }

    $data = array();
    $cmp = array();
    
    if ($interval != "hour") {
        parseInterval($data, $cmp, $query, $query_cmp, $interval);
    } else {
        for ($x = 0; $x < mysql_num_rows($query); $x++) {
            $data[] = mysql_fetch_assoc($query);

            if ( $query_cmp ) {
                $cmp[] = mysql_fetch_assoc($query_cmp);
                $cmp[$x]["CIRCUIT"] = $cmp[$x]["CIRCUIT"]." (".$_GET['compare_to'].")";
                $cmp[$x]["DATE_TIME"] = $data[$x]["DATE_TIME"];
//echo "CMP: ".$cmp;
                //$data[$x]["CMP_POWER_KWH"] = $cmp["POWER_KWH"];
                //$data[$x]["CMP_DATE_TIME"] = $cmp["DATE_TIME"];
            }
        }
    }
    
    if ( !$query_cmp )echo json_encode($data); 
    if ( $query_cmp ) echo json_encode(array_merge($data,$cmp));
    mysql_close($server);
?>