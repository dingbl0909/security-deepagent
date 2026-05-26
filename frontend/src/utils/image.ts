export type SelectedImage = {
  name: string;
  previewUrl: string;
  base64: string;
};

export function readImageFile(file: File): Promise<SelectedImage> {
  return new Promise((resolve, reject) => {
    if (!file.type.startsWith("image/")) {
      reject(new Error("请选择图片文件。"));
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = String(reader.result ?? "");
      if (!base64.startsWith("data:")) {
        reject(new Error("图片读取失败。"));
        return;
      }
      resolve({
        name: file.name,
        previewUrl: base64,
        base64,
      });
    };
    reader.onerror = () => reject(new Error("图片读取失败。"));
    reader.readAsDataURL(file);
  });
}
