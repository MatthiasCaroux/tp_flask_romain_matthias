from .app import *
from flask import render_template
from .models import Book, get_sample, get_author, get_book, AuthorForm, UserBookRating

from flask import url_for , redirect
from .app import db
from .models import Author

from flask_login import login_user, current_user, login_required
from flask import request

from .commands import newuser

from flask import flash
from werkzeug.utils import secure_filename



@app.route("/")
def home():
    return render_template("home.html", title="My Books !", books=get_sample(), bootstrap=bootstrap)


@app.route("/detail/<int:id>", methods=["GET", "POST"])
@login_required
def detail(id):
    book = Book.query.get_or_404(id)

    # Gestion du formulaire pour ajouter/modifier une note
    if request.method == 'POST' and 'rating' in request.form:
        rating = int(request.form['rating'])
        existing_rating = UserBookRating.query.filter_by(user_id=current_user.username, book_id=id).first()
        if existing_rating:
            existing_rating.rating = rating  # Mettre à jour la note existante
        else:
            new_rating = UserBookRating(user_id=current_user.username, book_id=id, rating=rating)
            db.session.add(new_rating)
        db.session.commit()
        flash('Votre note a été enregistrée', 'success')
        return redirect(url_for('detail', id=id))

    # Récupérer la note actuelle de l'utilisateur (s'il en a une)
    existing_rating = UserBookRating.query.filter_by(user_id=current_user.username, book_id=id).first()
    user_rating = existing_rating.rating if existing_rating else None

    return render_template("detail.html", book=book, user_rating=user_rating)




@app.route("/edit/author/<int:id>")
def edit_author(id):
    a = get_author(id)
    f = AuthorForm(id=a.id, name=a.name)
    return render_template("edit-author.html", author=a, form=f)


@app.route("/delete/author/<int:id>", methods=("POST",))
def confirm_delete_author(id):
    a = Author.query.get(id)
    if a:
        db.session.delete(a)
        db.session.commit()
        flash("Auteur supprimé avec succès.", "success")
    else:
        flash("Auteur non trouvé.", "error")
    return redirect(url_for('authors'))



@app.route("/delete/author/<int:id>/confirm", methods=["GET"])
def delete_author_confirm(id):
    author = Author.query.get(id)
    if not author:
        flash("Auteur non trouvé.", "error")
        return redirect(url_for('authors'))

    return render_template("delete_author_confirm.html", author=author)





@app.route("/save/author/", methods =("POST" ,))
def save_author():
    a = None
    f = AuthorForm()
    if f.validate_on_submit():
        id = int(f.id.data)
        a = get_author(id)
        a.name = f.name.data
        db.session.commit()
        return redirect(url_for('edit_author', id=a.id))
    a = get_author(int(f.id.data))
    return render_template("edit-author.html", author=a, form=f)


@app.route("/authors")
@login_required
def authors():
    return render_template("authors.html", authors=Author.query.all())

@app.route("/add/author", methods=("GET", "POST"))
def add_author():
    f = AuthorForm()
    if f.validate_on_submit():
        a = Author(name=f.name.data)
        db.session.add(a)
        db.session.commit()
        return redirect(url_for('authors'))
    return render_template("ajouter_auteur.html", form=f)



from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from .models import User
from hashlib import sha256

class LoginForm(FlaskForm):
    username = StringField('Username')
    password = PasswordField('Password')

    def get_authenticated_user(self):
        user = User.query.get(self.username.data)
        if user is None:
            return None
        m = sha256()
        m.update(self.password.data.encode())
        passwd = m.hexdigest()
        return user if user.password == passwd else None



@app.route("/login/", methods=("GET", "POST"))
def login():
    print("Login route accessed")  # print pour que je puisse debug
    f = LoginForm()
    if f.validate_on_submit():
        user = f.get_authenticated_user()
        if user is not None:
            login_user(user)
            print("Login form validated")
            return redirect(request.args.get('next') or url_for('home'))
    else:
        print("Login form not validated")  # print pour que je puisse debug
    return render_template("login.html", form=f)





from flask_login import logout_user
@app.route("/logout/")
def logout ():
    """
    Déconnecte l'utilisateur
    """
    logout_user()
    return redirect(url_for('home'))



@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate():
        print("le formulaire est validé")
        user = User(username=form.username.data, password=form.password.data)
        user.crypt_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))  # Rediriger après l'inscription réussie
    else : 
        print("probleme pour valider le formulaire de register")
    return render_template('register.html', form=form)



# Pour la partie favoris

@app.route("/favoris", methods=["GET"])
@login_required
def favoris():
    # Récupère directement la liste des livres favoris de l'utilisateur connecté
    favoris_livres = current_user.favorite_books
    print("coucou")
    print(favoris_livres)  # Ajoute cette ligne pour voir ce qui est récupéré
    return render_template("favoris.html", books=favoris_livres)




@app.route("/add_favorite/<int:book_id>", methods=["POST"])
@login_required
def add_favorite(book_id):
    # Récupère le livre en fonction de l'ID
    book = get_book(book_id)
    
    if not book:
        return redirect(url_for('home'))  # Si le livre n'existe pas, redirige vers l'accueil
    
    # Vérifie si le livre est déjà dans les favoris de l'utilisateur
    if book not in current_user.favorite_books:
        current_user.favorite_books.append(book)  # Ajoute le livre aux favoris
        db.session.commit()  # Sauvegarde dans la bd
    else:
        current_user.favorite_books.remove(book)
        db.session.commit()
    return redirect(url_for('detail', id=book_id))  # Redirige vers la page de détail du livre


# Pour la partie recherche

@app.route('/search', methods=['GET'])
def search_books():
    query = request.args.get('query')
    if query:
        results = Book.query.filter(Book.title.contains(query)).all()  # Remplace Book par ton modèle de livres
    else:
        results = []
    return render_template('search_results.html', books=results)


# Pour la partie creation d'un nouveau livre

from .models import BookForm, RegisterForm

# Chemin vers le dossier 'tuto' où se trouvent tes fichiers Flask
tuto_path = os.path.dirname(os.path.abspath(__file__))
# Définir le dossier de téléchargement
UPLOAD_FOLDER = os.path.join(tuto_path, 'static', 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# S'assurer que le dossier de téléchargement existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/add_book", methods=["GET", "POST"])
@login_required
def add_book():
    form = BookForm()
    form.author.choices = [(author.id, author.name) for author in Author.query.all()]

    if form.validate_on_submit():
        # Gérer l'upload de l'image
        if 'img' not in request.files:
            flash('Aucun fichier sélectionné', 'error')
            return redirect(request.url)

        file = request.files['img']
        if file.filename == '':
            flash('Pas de fichier sélectionné', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            img_url = os.path.join("", filename)

            # Créer un nouveau livre avec l'image
            book = Book(title=form.title.data, 
                        price=form.price.data, 
                        url=form.url.data, 
                        img=img_url,
                        author_id=form.author.data)

            db.session.add(book)
            db.session.commit()
            flash('Livre ajouté avec succès', 'success')
            return redirect(url_for('home'))
        else:
            flash('Format de fichier non supporté', 'error')

    else:
        if form.errors:
            flash('Erreur de validation du formulaire', 'error')

    return render_template("add_book.html", form=form)