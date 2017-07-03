const express = require('express')
const app = express()

app.get('/', function (req, res) {
  res.send('Hello World!')
})

var mongo = require('mongodb');
var monk = require('monk');
var db = monk('localhost:3000');

app.use(function(req,res,next){
    req.db = db;
    next();
});

app.listen(3000, function () {
  console.log('Example app listening on port 3000!')
})
