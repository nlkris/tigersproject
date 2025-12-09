#!/bin/bash
# sync.sh - Sync code and data between local and VM

KEY="github_action_key"
VM="kris@35.223.234.71"
LOCAL_DIR="/Users/kris/Documents/4AGMM/OutilsNUM/tigersproject"
VM_DIR="/home/kris/tigersproject"

# Chemins des fichiers de données
LOCAL_DATA="$LOCAL_DIR/data"
LOCAL_BACKEND_DATA="$LOCAL_DIR/backend/data"
VM_DATA="$VM_DIR/data"
VM_BACKEND_DATA="$VM_DIR/backend/data"

case "$1" in
    "pull")
        # Pull ALL data FROM VM to local
        echo "📥 Pulling ALL data from VM..."
        
        # 1. Pull JSON data files (data/)
        echo "  ↳ Pulling tweets.json and users.json..."
        scp -i $KEY $VM:$VM_DATA/tweets.json $LOCAL_DATA/
        scp -i $KEY $VM:$VM_DATA/users.json $LOCAL_DATA/
        
        # 2. Pull notifications.json (backend/data/)
        echo "  ↳ Pulling notifications.json..."
        # Créer le dossier local s'il n'existe pas
        mkdir -p $LOCAL_BACKEND_DATA
        scp -i $KEY $VM:$VM_BACKEND_DATA/notifications.json $LOCAL_BACKEND_DATA/
        
        # 3. Pull uploaded images (optional - can be large)
        read -p "  Download uploaded images too? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "  ↳ Pulling uploaded images..."
            rsync -avz -e "ssh -i $KEY" \
                --exclude='*.pyc' \
                $VM:$VM_DIR/backend/uploads/ \
                $LOCAL_DIR/backend/uploads/
        fi
        
        echo "✅ ALL data pulled from VM"
        ;;
        
    "push")
        # Push data FROM local to VM (OVERWRITES VM data!)
        echo "⚠️  WARNING: This will OVERWRITE VM data!"
        read -p "  Continue? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "📤 Pushing data to VM..."
            
            # 1. Push fichiers principaux (data/)
            scp -i $KEY $LOCAL_DATA/tweets.json $VM:$VM_DATA/
            scp -i $KEY $LOCAL_DATA/users.json $VM:$VM_DATA/
            
            # 2. Push notifications.json (backend/data/)
            echo "  ↳ Pushing notifications.json..."
            # Créer le dossier sur la VM si besoin
            ssh -i $KEY $VM "mkdir -p $VM_BACKEND_DATA"
            scp -i $KEY $LOCAL_BACKEND_DATA/notifications.json $VM:$VM_BACKEND_DATA/
            
            echo "✅ Data pushed to VM"
        fi
        ;;
        
    "deploy")
        # Deploy CODE only (preserves VM data)
        echo "🚀 Deploying code only..."
        
        # 1. Python files
        echo "  ↳ Deploying Python files..."
        scp -i $KEY $LOCAL_DIR/*.py $VM:$VM_DIR/
        scp -i $KEY $LOCAL_DIR/backend/*.py $VM:$VM_DIR/backend/ 2>/dev/null || true
        
        # 2. Templates
        echo "  ↳ Deploying templates..."
        scp -i $KEY -r $LOCAL_DIR/templates $VM:$VM_DIR/
        
        # 3. Static files (CSS, JS, images)
        echo "  ↳ Deploying static files..."
        scp -i $KEY -r $LOCAL_DIR/static $VM:$VM_DIR/ 2>/dev/null || true
        
        # 4. Data structure (folders only, not files)
        echo "  ↳ Ensuring data folders exist..."
        ssh -i $KEY $VM "mkdir -p $VM_DATA $VM_BACKEND_DATA $VM_DIR/backend/uploads"
        
        # 5. Restart app
        echo "  ↳ Restarting app..."
        ssh -i $KEY $VM "cd $VM_DIR && pkill -f python && nohup python3 app.py > app.log 2>&1 &"
        
        echo "✅ Code deployed (VM data preserved)"
        ;;
        
    "full-deploy")
        # Deploy EVERYTHING (code + data) - use with caution!
        echo "🌐 FULL deployment (code + data)..."
        read -p "  This overwrites VM data! Continue? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ./sync.sh deploy
            ./sync.sh push
            echo "✅ Full deployment complete"
        fi
        ;;
        
    "backup-vm")
        # Backup VM data to local backup folder
        echo "💾 Backing up VM data..."
        BACKUP_DIR="$LOCAL_DIR/backups/$(date +%Y%m%d_%H%M%S)"
        BACKUP_BACKEND_DIR="$BACKUP_DIR/backend"
        mkdir -p $BACKUP_DIR $BACKUP_BACKEND_DIR
        
        # Backup data files
        echo "  ↳ Backing up tweets.json and users.json..."
        scp -i $KEY $VM:$VM_DATA/tweets.json $BACKUP_DIR/ 2>/dev/null || echo "  ⚠️  tweets.json not found"
        scp -i $KEY $VM:$VM_DATA/users.json $BACKUP_DIR/ 2>/dev/null || echo "  ⚠️  users.json not found"
        
        # Backup notifications.json
        echo "  ↳ Backing up notifications.json..."
        scp -i $KEY $VM:$VM_BACKEND_DATA/notifications.json $BACKUP_BACKEND_DIR/ 2>/dev/null || echo "  ⚠️  notifications.json not found"
        
        echo "✅ VM data backed up to: $BACKUP_DIR"
        ;;
        
    "status")
        # Check VM status
        echo "🔍 Checking VM status..."
        ssh -i $KEY $VM "cd $VM_DIR && \
            echo '=== DATA STATUS ===' && \
            echo 'Tweets: \$(python3 -c \"import json, os; f=\\\"data/tweets.json\\\"; print(len(json.load(open(f))) if os.path.exists(f) else \\\"N/A\\\")\" 2>/dev/null || echo 'N/A')' && \
            echo 'Users: \$(python3 -c \"import json, os; f=\\\"data/users.json\\\"; print(len(json.load(open(f))) if os.path.exists(f) else \\\"N/A\\\")\" 2>/dev/null || echo 'N/A')' && \
            echo 'Notifications: \$(python3 -c \"import json, os; f=\\\"backend/data/notifications.json\\\"; print(len(json.load(open(f))) if os.path.exists(f) else \\\"N/A\\\")\" 2>/dev/null || echo 'N/A')' && \
            echo '' && \
            echo '=== APP STATUS ===' && \
            echo 'App running: \$(pgrep -f python3 | wc -l) processes' && \
            echo 'Disk usage: \$(du -sh . 2>/dev/null | cut -f1) in $VM_DIR' && \
            echo '' && \
            echo '=== LAST LOG ===' && \
            tail -5 app.log 2>/dev/null | sed 's/^/  /' || echo '  No log file'"
        ;;
        
    "pull-notifications")
        # Pull ONLY notifications
        echo "📥 Pulling notifications only..."
        mkdir -p $LOCAL_BACKEND_DATA
        scp -i $KEY $VM:$VM_BACKEND_DATA/notifications.json $LOCAL_BACKEND_DATA/
        echo "✅ Notifications pulled from VM"
        ;;
        
    "push-notifications")
        # Push ONLY notifications
        echo "📤 Pushing notifications only..."
        ssh -i $KEY $VM "mkdir -p $VM_BACKEND_DATA"
        scp -i $KEY $LOCAL_BACKEND_DATA/notifications.json $VM:$VM_BACKEND_DATA/
        echo "✅ Notifications pushed to VM"
        ;;
        
    *)
        echo "Usage: $0 {pull|push|deploy|full-deploy|backup-vm|status|pull-notifications|push-notifications}"
        echo ""
        echo "  pull                - Copy ALL data FROM VM to local (safe)"
        echo "  push                - Copy ALL data FROM local to VM (overwrites!)"
        echo "  deploy              - Deploy code only (preserves VM data)"
        echo "  full-deploy         - Deploy code + data (overwrites!)"
        echo "  backup-vm           - Backup VM data to local backups/"
        echo "  status              - Check VM status"
        echo "  pull-notifications  - Pull only notifications.json"
        echo "  push-notifications  - Push only notifications.json"
        echo ""
        echo "📌 Recommended workflow:"
        echo "  1. ./sync.sh pull              # Get latest VM data"
        echo "  2. Make code changes locally"
        echo "  3. ./sync.sh deploy            # Deploy code only"
        echo "  4. ./sync.sh pull-notifications # Update notifications"
        echo ""
        ;;
esac