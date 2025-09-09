# conferir o remoto atual
git remote -v

# corrigir a URL (remova a barra final e confirme o owner)
git remote set-url origin https://github.com/mbenedicto99/AI_Infra.git
# se preferir SSH (evita PAT):
# git remote set-url origin git@github.com:mbenedicto99/AI_Infra.git

git add -A
git commit -m "initial"  # se ainda não tiver commit
git branch -M main
git push -u origin main
