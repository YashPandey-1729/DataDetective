export function validateUpload(file: Pick<File, 'name' | 'size'>, image: boolean): string | null {
  const extension = file.name.toLowerCase().split('.').pop();
  const allowed = image ? ['png', 'jpg', 'jpeg'] : ['csv', 'xlsx', 'xls'];
  if (!extension || !allowed.includes(extension)) return image ? 'Choose a PNG or JPEG chart image.' : 'Choose a CSV or Excel dataset.';
  const limit = (image ? 5 : 15) * 1024 * 1024;
  if (file.size === 0) return 'The selected file is empty.';
  if (file.size > limit) return `The selected ${image ? 'image' : 'dataset'} exceeds ${image ? 5 : 15} MB.`;
  return null;
}
