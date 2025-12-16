"""
Interface Web FastAPI pour générer des certificats
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uuid
from datetime import datetime

router = APIRouter(prefix="/web", tags=["web"])

# Template HTML pour la forme
FORM_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Générateur de Certificats - EJBCA</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        
        .container {{
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            padding: 40px;
            max-width: 600px;
            width: 100%;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }}
        
        .header p {{
            color: #666;
            font-size: 14px;
        }}
        
        .form-group {{
            margin-bottom: 20px;
        }}
        
        label {{
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
            font-size: 14px;
        }}
        
        input[type="text"],
        input[type="email"],
        select {{
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 5px;
            font-size: 14px;
            transition: border-color 0.3s;
        }}
        
        input[type="text"]:focus,
        input[type="email"]:focus,
        select:focus {{
            outline: none;
            border-color: #667eea;
        }}
        
        .input-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        
        .full-width {{
            grid-column: 1 / -1;
        }}
        
        .button-group {{
            display: flex;
            gap: 10px;
            margin-top: 30px;
        }}
        
        button {{
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }}
        
        .btn-primary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }}
        
        .btn-secondary {{
            background: #f0f0f0;
            color: #333;
        }}
        
        .btn-secondary:hover {{
            background: #e0e0e0;
        }}
        
        .help-text {{
            font-size: 12px;
            color: #999;
            margin-top: 5px;
        }}
        
        .alert {{
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        
        .alert-info {{
            background: #e3f2fd;
            color: #1976d2;
            border-left: 4px solid #1976d2;
        }}
        
        .alert-success {{
            background: #e8f5e9;
            color: #388e3c;
            border-left: 4px solid #388e3c;
        }}
        
        .alert-warning {{
            background: #fff3e0;
            color: #f57c00;
            border-left: 4px solid #f57c00;
        }}
        
        .cert-info {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
            font-size: 13px;
            color: #666;
            line-height: 1.6;
        }}
        
        .cert-info strong {{
            color: #333;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Générateur de Certificats</h1>
            <p>Générez des certificats PKCS#12 pour vos applications</p>
        </div>
        
        <div class="alert alert-info">
            ℹ️ Remplissez le formulaire ci-dessous pour générer un nouveau certificat
        </div>
        
        <form method="POST" action="/web/generate">
            <div class="form-group">
                <label for="username">Nom d'utilisateur *</label>
                <input type="text" id="username" name="username" required placeholder="Ex: alice_prod">
                <div class="help-text">Identifiant unique pour l'utilisateur</div>
            </div>
            
            <div class="form-group">
                <label for="password">Mot de passe *</label>
                <input type="text" id="password" name="password" required placeholder="Mot de passe sécurisé">
                <div class="help-text">Doit être complexe (min 8 caractères)</div>
            </div>
            
            <div class="form-group">
                <label for="email">Email *</label>
                <input type="email" id="email" name="email" required placeholder="user@example.com">
                <div class="help-text">Adresse email de l'utilisateur</div>
            </div>
            
            <div class="form-group">
                <label for="cn">Common Name (CN) *</label>
                <input type="text" id="cn" name="cn" required placeholder="Ex: alice_prod">
                <div class="help-text">Nom du certificat (généralement = username)</div>
            </div>
            
            <div class="input-row">
                <div class="form-group">
                    <label for="org">Organisation</label>
                    <input type="text" id="org" name="org" value="ANSIE" placeholder="ANSIE">
                </div>
                <div class="form-group">
                    <label for="country">Pays (Code)</label>
                    <input type="text" id="country" name="country" value="DJ" placeholder="DJ">
                </div>
            </div>
            
            <div class="form-group">
                <label for="pkcs12_password">Mot de passe P12 *</label>
                <input type="text" id="pkcs12_password" name="pkcs12_password" required placeholder="Mot de passe du fichier P12">
                <div class="help-text">Mot de passe pour protéger le fichier PKCS#12</div>
            </div>
            
            <div class="button-group">
                <button type="submit" class="btn-primary">✨ Générer Certificat</button>
                <button type="reset" class="btn-secondary">Réinitialiser</button>
            </div>
        </form>
        
        <div class="cert-info">
            <strong>ℹ️ Information:</strong><br>
            • Les certificats sont générés au format PKCS#12 (fichier .p12)<br>
            • Durée de validité: 1 an<br>
            • Clé: RSA 2048 bits<br>
            • Autorité de Certification: ManagementCA
        </div>
    </div>
</body>
</html>
"""

SUCCESS_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Certificat Généré - EJBCA</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        
        .container {{
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            padding: 40px;
            max-width: 600px;
            width: 100%;
            text-align: center;
        }}
        
        .success-icon {{
            font-size: 60px;
            margin-bottom: 20px;
        }}
        
        h1 {{
            color: #388e3c;
            margin-bottom: 10px;
            font-size: 28px;
        }}
        
        p {{
            color: #666;
            margin-bottom: 20px;
            line-height: 1.6;
        }}
        
        .cert-details {{
            background: #f5f5f5;
            padding: 20px;
            border-radius: 5px;
            margin: 30px 0;
            text-align: left;
        }}
        
        .cert-details p {{
            margin: 10px 0;
            font-size: 14px;
        }}
        
        .cert-details strong {{
            color: #333;
            display: inline-block;
            width: 150px;
        }}
        
        .alert-success {{
            background: #e8f5e9;
            color: #388e3c;
            border-left: 4px solid #388e3c;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        
        .button-group {{
            display: flex;
            gap: 10px;
            margin-top: 30px;
        }}
        
        a, button {{
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s;
            display: inline-block;
        }}
        
        .btn-primary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }}
        
        .btn-secondary {{
            background: #f0f0f0;
            color: #333;
        }}
        
        .btn-secondary:hover {{
            background: #e0e0e0;
        }}
        
        .code {{
            background: #263238;
            color: #aed581;
            padding: 10px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            overflow-x: auto;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">✅</div>
        <h1>Certificat Généré avec Succès!</h1>
        
        <div class="alert-success">
            ✓ Votre certificat PKCS#12 a été généré et est prêt à télécharger
        </div>
        
        <div class="cert-details">
            <p><strong>Utilisateur:</strong> {username}</p>
            <p><strong>Fichier:</strong> {filename}</p>
            <p><strong>Taille:</strong> {size} bytes</p>
            <p><strong>Format:</strong> PKCS#12 (.p12)</p>
            <p><strong>Date:</strong> {date}</p>
            <p><strong>DN:</strong> {dn}</p>
        </div>
        
        <p>Cliquez ci-dessous pour télécharger votre certificat:</p>
        
        <div class="button-group">
            <a href="/web/download/{filename}" class="btn-primary">📥 Télécharger P12</a>
            <a href="/web/form" class="btn-secondary">← Générer Autre</a>
        </div>
        
        <div style="margin-top: 30px; padding: 20px; background: #fff3e0; border-radius: 5px;">
            <p style="color: #f57c00; margin: 0;">
                ⚠️ <strong>Important:</strong> Conservez ce fichier en sécurité. 
                Le mot de passe P12 est: <code style="background: #fff; padding: 2px 5px;">{p12_password}</code>
            </p>
        </div>
    </div>
</body>
</html>
"""

@router.get("/form", response_class=HTMLResponse)
async def get_form():
    """Affiche le formulaire de génération de certificat"""
    return FORM_HTML

@router.post("/generate", response_class=HTMLResponse)
async def generate_certificate(
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    cn: str = Form(...),
    org: str = Form("ANSIE"),
    country: str = Form("DJ"),
    pkcs12_password: str = Form(...)
):
    """Génère un certificat et affiche le succès"""
    from app.services.certificate_generator import generate_p12_certificate
    
    # Générer le certificat
    subject_dn = f"CN={cn},O={org},C={country}"
    
    try:
        p12_data, filename = generate_p12_certificate(
            username=username,
            subject_dn=subject_dn,
            pkcs12_password=pkcs12_password
        )
        
        # Sauvegarder le fichier
        certs_dir = Path("./generated_certs")
        certs_dir.mkdir(exist_ok=True)
        filepath = certs_dir / filename
        
        with open(filepath, 'wb') as f:
            f.write(p12_data)
        
        # Préparer les informations pour l'affichage
        size = len(p12_data)
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html = SUCCESS_HTML.format(
            username=username,
            filename=filename,
            size=size,
            date=date,
            dn=subject_dn,
            p12_password=pkcs12_password
        )
        
        return html
        
    except Exception as e:
        return f"""
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>❌ Erreur</h1>
                <p>Une erreur s'est produite: {str(e)}</p>
                <a href="/web/form">← Retour</a>
            </body>
        </html>
        """

@router.get("/download/{filename}")
async def download_certificate(filename: str):
    """Télécharge le certificat généré"""
    filepath = Path("./generated_certs") / filename
    
    if not filepath.exists():
        return {"error": "Fichier non trouvé"}
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/x-pkcs12"
    )

@router.get("/", response_class=HTMLResponse)
async def root():
    """Redirige vers le formulaire"""
    return """
    <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>Redirecting...</h1>
            <script>window.location.href = '/web/form';</script>
        </body>
    </html>
    """
