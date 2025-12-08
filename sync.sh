#!/bin/bash
# sync.sh - Sync code and data between local and VM

KEY="github_action_key"
VM="kris@35.223.234.71"
LOCAL_DIR="/Users/kris/Documents/4AGMM/OutilsNUM/tigersproject"
VM_DIR="/home/kris/tigersproject"

case "$1" in
    "pull")
        # Pull ALL data FROM VM to local
        echo "📥 Pulling ALL data from VM..."
        
        # 1. Pull JSON data files
        echo "  ↳ Pulling tweets.json and users.json..."
        scp -i $KEY $VM:$VM_DIR/data/tweets.json $LOCAL_DIR/data/
        scp -i $KEY $VM:$VM_DIR/data/users.json $LOCAL_DIR/data/
        
        # 2. Pull uploaded images (optional - can be large)
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
            scp -i $KEY $LOCAL_DIR/data/tweets.json $VM:$VM_DIR/data/
            scp -i $KEY $LOCAL_DIR/data/users.json $VM:$VM_DIR/data/
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
        
        # 4. Restart app
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
        mkdir -p $BACKUP_DIR
        
        # Backup data files
        scp -i $KEY $VM:$VM_DIR/data/tweets.json $BACKUP_DIR/
        scp -i $KEY $VM:$VM_DIR/data/users.json $BACKUP_DIR/
        
        echo "✅ VM data backed up to: $BACKUP_DIR"
        ;;
        
    "status")
        # Check VM status
        echo "🔍 Checking VM status..."
        ssh -i $KEY $VM "cd $VM_DIR && \
            echo 'Tweets: \$(python3 -c \"import json; print(len(json.load(open(\"data/tweets.json\"))))\" 2>/dev/null || echo 'N/A')' && \
            echo 'Users: \$(python3 -c \"import json; print(len(json.load(open(\"data/users.json\"))))\" 2>/dev/null || echo 'N/A')' && \
            echo 'App running: \$(pgrep -f python3 | wc -l) processes' && \
            echo 'Last log: \$(tail -1 app.log 2>/dev/null || echo \"No log\")'"
        ;;
        
    *)
        echo "Usage: $0 {pull|push|deploy|full-deploy|backup-vm|status}"
        echo ""
        echo "  pull         - Copy data FROM VM to local (safe)"
        echo "  push         - Copy data FROM local to VM (overwrites!)"
        echo "  deploy       - Deploy code only (preserves VM data)"
        echo "  full-deploy  - Deploy code + data (overwrites!)"
        echo "  backup-vm    - Backup VM data to local backups/"
        echo "  status       - Check VM status"
        echo ""
        echo "📌 Recommended workflow:"
        echo "  1. ./sync.sh pull        # Get latest VM data"
        echo "  2. Make code changes locally"
        echo "  3. ./sync.sh deploy      # Deploy code only"
        echo ""
        ;;
esac