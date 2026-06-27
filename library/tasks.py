import io
from django.core.management import call_command
from library.models import BookImportTask

def run_import_task(task_id, file_path):
    """
    Background worker function that runs the import_books command
    and updates the BookImportTask with the final log and status.
    """
    try:
        task = BookImportTask.objects.get(id=task_id)
    except BookImportTask.DoesNotExist:
        return
        
    task.status = 'PROCESSING'
    task.save()
    
    out = io.StringIO()
    err = io.StringIO()
    
    try:
        call_command('import_books', file_path, '--no-color', f'--task-id={task_id}', stdout=out, stderr=err)
        task.status = 'COMPLETED'
    except Exception as e:
        task.status = 'FAILED'
        err.write(f"\nFatal Error: {str(e)}")
        
    log = out.getvalue()
    if err.getvalue():
        log += "\nErrors:\n" + err.getvalue()
        
    task.import_log = log
    task.save()
