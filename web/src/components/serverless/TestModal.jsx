import { AlertDialog, AlertDialogContent, Button } from '../tailadmin-ui'

export default function TestModal({ onClose }) {
  return (
    <AlertDialog open={true} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent className="max-w-md">
        <div className="p-6 bg-dark-surface-card">
          <h2 className="text-xl text-white mb-4">Modal de Teste</h2>
          <p className="text-gray-400 mb-4">Se você está vendo isso, o modal funciona!</p>
          <Button variant="primary" onClick={onClose}>
            Fechar
          </Button>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  )
}
