//import express module 
const express = require('express');
//create an express app
const  app = express();
//require express middleware body-parser
const bodyParser = require('body-parser');

//set the view engine to ejs
app.set('view engine', 'ejs');
//set the directory of views
app.set('views', './views');
//specify the path of static directory
app.use(express.static(__dirname + '/public'));

//use body parser to parse JSON and urlencoded request bodies
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

//By Default we have 3 books
var books = [
    { "BookID": "1", "Title": "Book 1", "Author": "Author 1" },
    { "BookID": "2", "Title": "Book 2", "Author": "Author 2" },
    { "BookID": "3", "Title": "Book 3", "Author": "Author 3" }
]
//route to root
app.get('/', function (req, res) {
  res.render('home', { books });
});




// add code to render the create view
app.get('/add-book', function (req, res) {
  res.render('create');
});

// add your code to create new book
app.post('/add-book', function (req, res) {
  const { Title, Author } = req.body;

  const nextId = books.length
    ? (Math.max(...books.map(b => parseInt(b.BookID, 10))) + 1).toString()
    : "1";

  books.push({ BookID: nextId, Title, Author });
  res.redirect('/');
});




app.get('/update-book/:id', function (req, res) {
  const bookId = req.params.id;
  const book = books.find(b => b.BookID === bookId);

  if (!book) {
    return res.status(404).send("Book not found");
  }

  res.render('update', { book });
});


app.post('/update-book/:id', function (req, res) {
  const bookId = req.params.id;
  const { Title, Author } = req.body;

  const book = books.find(b => b.BookID === bookId);
  if (book) {
    book.Title = Title;
    book.Author = Author;
  }

  res.redirect('/');
});




// add code to render the delete view
app.get('/delete-book', function (req, res) {
  res.render('delete');
});

// add code to delete a book
app.post('/delete-book', function (req, res) {
  if (!books.length) return res.redirect('/');

  const maxId = Math.max(...books.map(b => parseInt(b.BookID, 10)));
  const idx = books.findIndex(b => parseInt(b.BookID, 10) === maxId);
  if (idx > -1) books.splice(idx, 1);

  res.redirect('/');
});




app.listen(8080, function () {
    console.log("Server listening on port 8080");
});