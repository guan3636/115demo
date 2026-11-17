document.addEventListener('submit', function (event) {
  const message = event.target.dataset.confirm;
  if (message && !window.confirm(message)) event.preventDefault();
});

// Registration: display a short description for the selected role.
const roleInputs = document.querySelectorAll('#register-form input[name="role"]');
if (roleInputs.length) {
  const note = document.getElementById('role-note');
  function updateRole() {
    const isEditor = document.querySelector('#register-form input[name="role"]:checked')?.value === 'editor';
    if (note) note.textContent = isEditor
      ? '編輯者可查看待審稿件，並決定通過或退回。'
      : '作者可新增、修改、刪除與送審自己的文章。';
  }
  roleInputs.forEach(input => input.addEventListener('change', updateRole));
  updateRole();
}
