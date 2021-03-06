/*******************************************************************************
 * Copyright (c) 2017 Kumar Rishabh and others.
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Apache License, Version 2.0
 * which accompanies this distribution, and is available at
 * http://www.apache.org/licenses/LICENSE-2.0
 *******************************************************************************/

var express = require('express');
var router = express.Router();

/* Post controller for VNF_TAG Association */
router.post('/', function(req, res) {
  req.checkBody("tag_name", "TAG Name must not be empty").notEmpty();
  req.checkBody("vnf_name", "VNF Name must not be empty").notEmpty();

  var errors = req.validationErrors();
  console.log(errors);

  var response = '';  for(var i = 0; i < errors.length; i++) {
    console.log(errors[i]['msg']);
    response = response + errors[i]['msg'] + '; ';
  }

  if(errors) {  res.status(500);
    res.send({'error': response});
    return;
  }

  var tag_name = req.param('tag_name');
  var vnf_name = req.param('vnf_name');

  db_pool.getConnection(function(err, connection) {
    // Use the connection
    //sql_query = 'INSERT INTO tag SET ?'
    sql_query = 'insert into vnf_tags(vnf_id, tag_id) values ((select vnf_id from vnf where vnf_name = \'' + vnf_name + '\'), (select tag_id from tag where tag_name = \'' + tag_name + '\'))';
    console.log(sql_query);
    connection.query(sql_query, function (error, results, fields) {
        // And done with the connection.

        connection.release();
        res.end('{"success" : "Updated Successfully", "status" : 200}');

        // Handle error after the release.
        if (error) throw error;
        // Don't use the connection here, it has been returned to the pool.
    });
  });

  res.end('{"success" : "Updated Successfully", "status" : 200}');
  //res.render('vnf_tag_association', { title: 'Express' });
});

module.exports = router;
