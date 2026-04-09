from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, List
import json
from pathlib import Path

# 导入引擎
from database.cigar_db import db
from engines.image_engine import recognizer
from engines.history_engine import history

app = FastAPI(title="Cigar Intelligence System", version="1.0.0")

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 模板
Path("templates").mkdir(exist_ok=True)
templates = Jinja2Templates(directory="templates")

# 确保上传目录存在
Path("static/uploads").mkdir(parents=True, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    brands = db.get_all_brands()
    origins = db.get_all_origins()
    recent = history.get_recent_searches(5)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "brands": brands,
        "origins": origins,
        "recent_searches": recent
    })

@app.get("/health")
async def health():
    """健康检查端点 - 不加载数据库以快速响应"""
    return {"status": "ok", "version": "1.0.0", "timestamp": "2024"}

@app.get("/api/search")
async def search(
    q: str,
    brand: Optional[str] = None,
    wrapper: Optional[str] = None,
    binder: Optional[str] = None,
    filler: Optional[str] = None,
    cigar_type: Optional[str] = None,
    limit: int = 10
):
    """搜索API - 模糊搜索 + 交叉筛选"""
    
    # 1. 模糊搜索
    fuzzy_results = db.search_fuzzy(q, limit=20)
    
    # 2. 交叉筛选
    filtered = db.filter_by_criteria(
        brand=brand,
        wrapper=wrapper,
        binder=binder,
        filler=filler,
        cigar_type=cigar_type
    )
    
    # 3. 取交集
    filtered_ids = {p.model_id for p in filtered}
    
    final_results = []
    for result in fuzzy_results:
        product = result['product']
        if product.model_id in filtered_ids or not any([brand, wrapper, binder, filler, cigar_type]):
            # 检查配方模糊提醒
            fuzzy_warning = None
            if wrapper and wrapper != "all" and wrapper in product.blend_wrapper:
                if product.fuzzy_blend:
                    fuzzy_warning = "⚠️ 该产品配方信息有限，筛选结果仅供参考"
            
            final_results.append({
                'id': product.model_id,
                'name': product.model_name,
                'brand': product.brand_name,
                'series': product.series_name,
                'type': product.type,
                'size': f"{product.length_mm}mm x {product.ring_gauge}环" if product.length_mm and product.ring_gauge else "未知",
                'price': f"¥{product.price_box}/盒" if product.price_box else "价格未知",
                'blend': {
                    'wrapper': product.blend_wrapper,
                    'binder': product.blend_binder,
                    'filler': product.blend_filler,
                    'fuzzy': product.fuzzy_blend
                },
                'verified': product.verified,
                'match_score': result['score'],
                'warning': fuzzy_warning
            })
    
    # 记录搜索历史
    history.add_record(
        query_type='text',
        query_content=q,
        results_count=len(final_results),
        filters_used={
            'brand': brand,
            'wrapper': wrapper,
            'binder': binder,
            'filler': filler
        }
    )
    
    return JSONResponse({
        'query': q,
        'filters': {
            'brand': brand,
            'wrapper': wrapper,
            'binder': binder,
            'filler': filler,
            'type': cigar_type
        },
        'total': len(final_results),
        'results': final_results[:limit]
    })

@app.get("/api/suggest")
async def suggest(q: str, limit: int = 5):
    """搜索建议API"""
    results = db.search_fuzzy(q, limit=limit)
    
    suggestions = []
    for result in results:
        p = result['product']
        suggestions.append({
            'id': p.model_id,
            'name': f"{p.brand_name} {p.model_name}",
            'score': result['score']
        })
    
    return JSONResponse({'suggestions': suggestions})

@app.post("/api/recognize")
async def recognize_image(file: UploadFile = File(...)):
    """图片识别API"""
    from PIL import Image
    import io
    
    # 读取图片
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    
    # 保存上传的图片
    upload_path = f"static/uploads/{file.filename}"
    with open(upload_path, "wb") as f:
        f.write(contents)
    
    # 识别
    matches = recognizer.recognize(image, top_k=5)
    
    results = []
    for match in matches:
        p = match['product']
        results.append({
            'id': p.model_id,
            'name': p.model_name,
            'brand': p.brand_name,
            'confidence': match['confidence'],
            'score': match['score'],
            'reasons': match['reasons'],
            'blend': {
                'wrapper': p.blend_wrapper,
                'binder': p.blend_binder,
                'filler': p.blend_filler
            },
            'image_url': f"/static/uploads/{file.filename}"
        })
    
    # 记录历史
    history.add_record(
        query_type='image',
        query_content=f"[图片] {file.filename}",
        results_count=len(results),
        confidence=results[0]['score'] / 100 if results else 0
    )
    
    return JSONResponse({
        'image_url': f"/static/uploads/{file.filename}",
        'matches': results
    })

@app.get("/api/product/{product_id}")
async def product_detail(product_id: str):
    """产品详情API"""
    product = db.get_product_by_id(product_id)
    
    if not product:
        return JSONResponse({'error': 'Product not found'}, status_code=404)
    
    return JSONResponse({
        'id': product.model_id,
        'name': product.model_name,
        'brand': product.brand_name,
        'series': product.series_name,
        'type': product.type,
        'size': {
            'length': product.length_mm,
            'ring_gauge': product.ring_gauge
        },
        'price': {
            'box': product.price_box,
            'unit': product.price_unit
        },
        'packaging': product.packaging,
        'blend': {
            'wrapper': product.blend_wrapper,
            'binder': product.blend_binder,
            'filler': product.blend_filler,
            'notes': product.blend_notes,
            'verified': product.verified,
            'fuzzy': product.fuzzy_blend
        },
        'flavor': product.flavor,
        'features': product.features
    })

@app.get("/api/history")
async def get_history():
    """获取搜索历史"""
    return JSONResponse({
        'recent': history.get_recent_searches(10),
        'statistics': history.get_statistics()
    })

@app.delete("/api/history")
async def clear_history():
    """清空搜索历史"""
    history.clear_history()
    return JSONResponse({'message': 'History cleared'})

@app.get("/api/filters/options")
async def filter_options():
    """获取筛选选项"""
    return JSONResponse({
        'brands': db.get_all_brands(),
        'origins': db.get_all_origins(),
        'types': ['手工', '机制', '半叶卷', '手卷']
    })

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
