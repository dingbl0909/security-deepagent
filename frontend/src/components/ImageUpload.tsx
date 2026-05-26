import { useRef } from "react";
import type { SelectedImage } from "../utils/image";

type ImageUploadProps = {
  selectedImage: SelectedImage | null;
  disabled?: boolean;
  visionEnabled?: boolean;
  onSelect: (file: File) => void;
  onClear: () => void;
  error?: string;
};

export function ImageUpload({
  selectedImage,
  disabled = false,
  visionEnabled = false,
  onSelect,
  onClear,
  error,
}: ImageUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="image-upload">
      <div className="image-upload-header">
        <div>
          <span className="review-label">安防物品研判</span>
          <p className="muted image-upload-tip">
            {visionEnabled
              ? "上传现场抓拍或图片，系统会委派 object-analyst 进行多模态识别。"
              : "后端未启用 vision 能力，上传后需要先配置 SECURITY_AGENT_VISION_ENABLED=true。"}
          </p>
        </div>
        <div className="image-upload-actions">
          <button type="button" disabled={disabled} onClick={() => inputRef.current?.click()}>
            选择图片
          </button>
          {selectedImage ? (
            <button type="button" disabled={disabled} onClick={onClear}>
              移除
            </button>
          ) : null}
        </div>
      </div>

      <input
        ref={inputRef}
        className="image-upload-input"
        type="file"
        accept="image/*"
        disabled={disabled}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) {
            onSelect(file);
          }
          event.target.value = "";
        }}
      />

      {error ? <div className="error-banner">{error}</div> : null}

      {selectedImage ? (
        <div className="image-preview">
          <img src={selectedImage.previewUrl} alt={selectedImage.name} />
          <div className="image-preview-meta">
            <strong>{selectedImage.name}</strong>
            <span>已附加到下一次分析请求</span>
          </div>
        </div>
      ) : (
        <div className="image-upload-empty">支持 JPG、PNG、WEBP 等常见图片格式。</div>
      )}
    </div>
  );
}
